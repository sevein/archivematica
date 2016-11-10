# This file is part of Archivematica.
#
# Copyright 2010-2013 Artefactual Systems Inc. <http://artefactual.com>
#
# Archivematica is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Archivematica is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Archivematica.  If not, see <http://www.gnu.org/licenses/>.

from django.http import HttpResponse, HttpResponseNotFound

from mcpserver import Client as MCPServerClient


def approve_job(request):
    try:
        job_uuid = request.REQUEST['uuid']
        choice_id = request.REQUEST['choice']
        uid = request.REQUEST['uid'] # This should not be here? TODO
    except KeyError:
        return HttpResponseNotFound()
    else:
        approved = MCPServerClient().approve_job(job_uuid, choice_id)
        if approved:
            return HttpResponse(status=202)
        return HttpResponse(status=503)

