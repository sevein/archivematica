import grpc

import protos.mcpserver_pb2


class Client(object):
    """
    MCPServer client using the gRPC protocol.
    """
    def __init__(self, address='localhost:50051'):
        self.channel = grpc.insecure_channel(address)
        self.stub = protos.mcpserver_pb2.MCPServerStub(self.channel)

    def approve_transfer(self, sip_uuid):
        resp = self.stub.ApproveTransfer(protos.mcpserver_pb2.ApproveTransferRequest(UUID=sip_uuid))
        return resp.approved

    def approve_job(self, job_uuid, chain_uuid):
        resp = self.stub.ApproveJob(protos.mcpserver_pb2.ApproveJobRequest(UUID=job_uuid, chainUUID=chain_uuid))
        return resp.approved

    def list_jobs_awaiting_approval(self):
        return self.stub.ListJobsAwaitingApproval(protos.mcpserver_pb2.Empty())

    def list_microservice_choice_replacements(self, microservice_uuid=None, description=None):
        request = protos.mcpserver_pb2.ListMicroserviceChoiceReplacementsRequest(microserviceUUID=microservice_uuid, description=description)
        return self.stub.ListMicroserviceChoiceReplacements(request)

    def get_microservice_choice_replacement_arguments(self, microservice_uuid=None, description=None):
        request = protos.mcpserver_pb2.ListMicroserviceChoiceReplacementsRequest(microserviceUUID=microservice_uuid, description=description)
        resp = self.stub.ListMicroserviceChoiceReplacements(request)
        try:
            config = resp.replacements[0].arguments
        except KeyError:
            raise Exception('Not found!')
        else:
            return dict(config)

    def set_microservice_choice_replacement(self, arguments, microservice_uuid=None, description=None):
        if not isinstance(arguments, dict):
            raise ValueError('arguments parameter must be a dict')
        request = protos.mcpserver_pb2.SetMicroserviceChoiceReplacementRequest(microserviceUUID=microservice_uuid, description=description, arguments=arguments)
        return self.stub.SetMicroserviceChoiceReplacement(request)

    def list_microservice_choice_duplicates(self, link_name, choice_name):
        request = protos.mcpserver_pb2.ListMicroserviceChoiceDuplicatesRequest(linkName=link_name, choiceName=choice_name)
        return self.stub.ListMicroserviceChoiceDuplicates(request).duplicates


"""
PLEASE IGNORE THIS! IT IS JUST A CLIENT FOR TESTING PURPOSES!
"""
if __name__ == '__main__':
    import sys
    if len(sys.argv) == 1:
        sys.exit('Missing parameter')
    cmd = sys.argv[1]
    client = Client()
    if cmd == 'ListJobsAwaitingApproval':
        resp = client.list_jobs_awaiting_approval()
        jobs = resp.jobs
        for job in jobs:
            print("\nJob {} of unit with type {}".format(job.UUID, protos.mcpserver_pb2.ListJobsAwaitingApprovalResponse.Job.UnitType.Name(job.unitType)))
            for item in job.choices:
                print("\tChoice: {} (value={})".format(item.description, item.value))
        print("Transfer count:", resp.transferCount)
        print("Ingest count:", resp.ingestCount)
    elif cmd == 'ApproveJob':
        try:
            job_uuid = sys.argv[2]
            choice_uuid = sys.argv[3]
        except IndexError:
            sys.exit('Missing parameters (job_uuid, choice_uuid)')
        else:
            approved = client.approve_job(job_uuid, choice_uuid)
            print("Has the job been approved? {}".format("Yes!" if approved else "No, :("))
    elif cmd == 'ApproveTransfer':
        try:
            sip_uuid = sys.argv[2]
        except IndexError:
            sys.exit('Missing parameter (sip_uuid)')
        else:
            approved = client.approve_transfer(sip_uuid)
            print("Has the transfer been approved? {}".format("Yes!" if approved else "No, :("))
    elif cmd == 'ListMicroserviceChoiceReplacements':
        try:
            description = sys.argv[2]
        except IndexError:
            print(client.list_microservice_choice_replacements())
        else:
            print(client.get_microservice_choice_replacement_arguments(description=description))
    elif cmd == 'SetMicroserviceChoiceReplacement':
        if len(sys.argv) < 3:
            sys.exit('Missing parameters, I expect something like: `mcpserver.py SetMicroserviceChoiceReplacement Name foo=bar ping=pong')
        description = sys.argv[2]
        arguments = {}
        for arg in sys.argv[3:]:
            parts = arg.split('=')
            if len(parts) != 2:
                continue
            arguments[parts[0]] = parts[1]
        print(client.set_microservice_choice_replacement(arguments, description=description))
    elif cmd == 'ListMicroserviceChoiceDuplicates':
        try:
            link_name = sys.argv[2]
            choice_name = sys.argv[3]
        except IndexError:
            sys.exit('Missing parameter (link_name, choice_name)')
        else:
            print(client.list_microservice_choice_duplicates(link_name, choice_name))
    else:
        sys.exit('Unknown command ({}), try: ListJobsAwaitingApproval, ApproveJob'.format(cmd))
    print("")
