import ast
from concurrent import futures
import logging
import time

import grpc
import six

from django.db import connection

# This import is important! It's here so jobChain is imported before
# linkTaskManagerChoice is imported. The old RPCServer module was doing the
# same but it was not documented. This is easy to fix but it requires some
# refactoring.
import archivematicaMCP

from linkTaskManagerChoice import choicesAvailableForUnits as _global_shared_awaiting_jobs_choices

from main import models
from protos import mcpserver_pb2


logger = logging.getLogger("archivematica.mcp.server.grpc")

_ONE_DAY_IN_SECONDS = 60 * 60 * 24


def log_rpc(func):
    def _decorated(*args, **kwargs):
        logger.debug("rpc %s", func.func_name)
        request = args[1]
        for name, _ in six.iteritems(request.DESCRIPTOR.fields_by_camelcase_name):
            # Unpacked, but I don't need the `google.protobuf.descriptor.FieldDescriptor` for now
            try:
                value = getattr(request, name)
            except AttributeError:
                logger.debug("Parameter %s received but it is unknown? (type %s)", name, type(value).__name__)
            else:
                logger.debug("Parameter %s received (type %s)", name, type(value).__name__)

        return func(*args, **kwargs)
    return _decorated


class gRPCServer(object):
    """
    TODO:
    - Follow conventions in https://developers.google.com/protocol-buffers/docs/style -> s/UUID/id, s/microserviceUUID/microserviceId
    - microserviceId? linkId? chainId?
    - https://gist.github.com/sevein/75732d85e129348dc32e6c4b15982bf8#dashboard
    - Should I lock _global_shared_awaiting_jobs_choices for reads?
    - Make possible to setup user_id and pass via context: https://groups.google.com/d/msg/grpc-io/NbismJeAQDk/duEsjFOGCgAJ
    - Confirm that is thread-safe.
    - Think on ways to instantiate based on local Dashboard config, and be able to reuse.
    - Make sure that it doesn't expose pb2 objects until we understand how they work.
    - ApproveJob: chain_uuid should be choice_id as it can have values of different nature? ints, uuids...
    - Tests
    - gRPCServer.py should use config.*
    - Search for TODOS!
    - Statuses code here: https://github.com/grpc/grpc/blob/master/doc/statuscodes.md
    - Order imports properly
    - Think about the concept of shareable models on the client side, is necessary?
      I want to add behaviour to the replacementdic resopnse, for example. the client
      is cumbersombe. I don't want to do this:
        ```
            replacements = MCPServerClient().list_microservice_choice_replacements(description='ArchivesSpace Config').replacements
            if len(replacements) == 0:
                print("Unable to fetch the replacement dictionary")
                return None
            config = dict(replacements[0].arguments)
        ```

    Style to implement methods in this class:
    - Start creating the `response = ...` because you always have to return it
    - Always use `context.set_code(grpc.StatusCode.NOT_FOUND)` properly
    """

    _UNIT_TYPES = {
        'SIP': mcpserver_pb2.ListJobsAwaitingApprovalResponse.Job.UnitType.Value('INGEST'),
        'Transfer': mcpserver_pb2.ListJobsAwaitingApprovalResponse.Job.UnitType.Value('TRANSFER'),
    }

    def __init__(self):
        # Do you need to initialize? This is the place.
        pass

    @log_rpc
    def ApproveTransfer(self, request, context):
        """
        Look up the transfer given its UUID. Proceed only if the choice is a
        'Approve transfer'.
        """
        resp = mcpserver_pb2.ApproveTransferResponse()
        for job_uuid, task_manager in _global_shared_awaiting_jobs_choices.items():
            unit_uuid = task_manager.unit.UUID
            if request.UUID != unit_uuid:
                continue
            for item in task_manager.choices:
                value = item[0]
                description = item[1]
                if description != 'Approve transfer':
                    continue
                match = task_manager
                break
        try:
            match
        except NameError:
            context.set_code(grpc.StatusCode.NOT_FOUND)
        else:
            match.proceedWithChoice(value, user_id=None)
            resp.approved = True
        return resp

    @log_rpc
    def ApproveJob(self, request, context):
        """
        Approve the job requested only if avaiable.
        """
        resp = mcpserver_pb2.ApproveJobResponse()
        if request.UUID not in _global_shared_awaiting_jobs_choices:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            return resp
        _global_shared_awaiting_jobs_choices[request.UUID].proceedWithChoice(request.chainUUID, user_id=None)
        resp.approved = True
        return resp

    @log_rpc
    def ListJobsAwaitingApproval(self, request, context):
        resp = mcpserver_pb2.ListJobsAwaitingApprovalResponse(transferCount=0, ingestCount=0)

        for job_uuid, task_manager in _global_shared_awaiting_jobs_choices.items():
            task_manager_class_name = type(task_manager).__name__
            unit_class_name = type(task_manager.unit).__name__

            # Omit if hidden
            try:
                if task_manager.unit.hidden:
                    continue
            except AttributeError:
                pass

            # Update counters
            if unit_class_name == 'Transfer':
                resp.transferCount += 1
            elif unit_class_name == 'SIP':
                resp.ingestCount += 1
            else:
                continue

            # Each element in the global shared dictionary represents a job
            # with a set of choices. These choices are structured differently
            # based on the type of task manager.
            job = resp.jobs.add()
            job.UUID = job_uuid
            job.unitType = self._UNIT_TYPES.get(unit_class_name)
            for item in task_manager.choices:
                choice = job.choices.add()
                choice.description = item[1]
                if task_manager_class_name == 'linkTaskManagerReplacementDicFromChoice':
                    choice.value = str(item[0])  # Option ID: 0, 1, 2, 3...
                elif task_manager_class_name in ('linkTaskManagerChoice', 'linkTaskManagerGetUserChoiceFromMicroserviceGeneratedList'):
                    choice.value = item[0]  # UUID

        return resp

    @log_rpc
    def ListMicroserviceChoiceReplacements(self, request, context):
        resp = mcpserver_pb2.ListMicroserviceChoiceReplacementsResponse()
        filter_params = {}
        if request.microserviceUUID:
            filter_params['choiceavailableatlink_id'] = request.microserviceUUID
        if request.description:
            filter_params['description'] = request.description
        for item in models.MicroServiceChoiceReplacementDic.objects.filter(**filter_params):
            repl = resp.replacements.add()
            repl.microserviceUUID = item.choiceavailableatlink.id
            repl.description = item.description
            try:
                args = ast.literal_eval(item.replacementdic)
            except (ValueError, SyntaxError):
                continue
            else:
                for k, v in six.iteritems(args):
                    repl.arguments[k] = v
        return resp

    @log_rpc
    def SetMicroserviceChoiceReplacement(self, request, context):
        resp = mcpserver_pb2.Empty()
        get_params = {}
        if request.microserviceUUID:
            get_params['choiceavailableatlink_id'] = request.microserviceUUID
        if request.description:
            get_params['description'] = request.description
        arguments = request.arguments
        if not arguments:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            return resp
        try:
            mscrd = models.MicroServiceChoiceReplacementDic.objects.get(**get_params)
        except models.MicroServiceChoiceReplacementDic.DoesNotExist:
            logger.debug("The MicroServiceChoiceReplacementDic requested cannot be found")
            context.set_code(grpc.StatusCode.NOT_FOUND)
        else:
            mscrd.replacementdic = str(arguments)
            mscrd.save()
        return resp

    @log_rpc
    def ListMicroserviceChoiceDuplicates(self, request, context):
        resp = mcpserver_pb2.ListMicroserviceChoiceDuplicatesResponse()
        if not all((request.linkName, request.choiceName)):
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            return resp
        sql = """
            SELECT
                MicroServiceChainLinks.pk,
                MicroServiceChains.pk
            FROM TasksConfigs
            LEFT JOIN MicroServiceChainLinks ON (MicroServiceChainLinks.currentTask = TasksConfigs.pk)
            LEFT JOIN MicroServiceChainChoice ON (MicroServiceChainChoice.choiceAvailableAtLink = MicroServiceChainLinks.pk)
            LEFT JOIN MicroServiceChains ON (MicroServiceChains.pk = MicroServiceChainChoice.chainAvailable)
            WHERE
                TasksConfigs.description = %s
                AND MicroServiceChains.description = %s;
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [request.linkName, request.choiceName])
            for item in cursor:
                dup = resp.duplicates.add()
                dup.srcUUID = item[0]
                dup.dstUUID = item[1]
        return resp


def start():
    """
    Start our gRPC server with which our RPCs can be serviced. We pass our own
    pool of threads (futures.ThreadPoolExecutor) that we want the server to use
    to service the RPCs.
    """
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=5))
    mcpserver_pb2.add_MCPServerServicer_to_server(gRPCServer(), server)

    # We can afford to do this as long as Archivematica runs in a box.
    # Hoping not to do that for much longer though.
    addr = '[::]:50051'
    server.add_insecure_port(addr)
    logger.info('gRPC server listening on %s', addr)

    server.start()
    try:
        while True:
            time.sleep(_ONE_DAY_IN_SECONDS)
    except KeyboardInterrupt:
        server.stop(0)
