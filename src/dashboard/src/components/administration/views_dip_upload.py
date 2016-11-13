from django.contrib import messages
from django.shortcuts import render

from components.administration.forms_dip_upload import ArchivesSpaceConfigForm, ArchivistsToolkitConfigForm, AtomConfigForm
from components.administration.models import ReplacementDict


_AS_DICTNAME = 'at_dip_upload'
_ATK_DICTNAME = 'atk_dip_upload'
_ATOM_DICTNAME = 'atom_dip_upload'


def admin_as(request):
    """ View to configure ArchivesSpace DIP upload. """
    if request.method == 'POST':
        form = ArchivesSpaceConfigForm(request.POST)
        if form.is_valid():
            ReplacementDict.objects.set_arguments(_AS_DICTNAME, form.cleaned_data)
            messages.info(request, 'Saved.')
    else:
        form = ArchivesSpaceConfigForm(initial=ReplacementDict.objects.get_arguments(_AS_DICTNAME))
    return render(request, 'administration/dips_as_edit.html', {'form': form})


def admin_atk(request):
    """ View to configure Archivist's Toolkit DIP upload. """
    if request.method == 'POST':
        form = ArchivistsToolkitConfigForm(request.POST)
        if form.is_valid():
            ReplacementDict.objects.set_arguments(_ATK_DICTNAME, form.cleaned_data)
            messages.info(request, 'Saved.')
    else:
        form = ArchivistsToolkitConfigForm(initial=ReplacementDict.objects.get_arguments(_ATK_DICTNAME))
    return render(request, 'administration/dips_atk_edit.html', {'form': form})


def admin_atom(request):
    """ View to configure AtoM DIP upload. """
    if request.method == 'POST':
        form = AtomConfigForm(request.POST)
        if form.is_valid():
            ReplacementDict.objects.set_arguments(_ATOM_DICTNAME, form.cleaned_data)
            messages.info(request, 'Saved.')
    else:
        form = AtomConfigForm(initial=ReplacementDict.objects.get_arguments(_ATOM_DICTNAME))
    return render(request, 'administration/dips_atom_edit.html', {'form': form})


"""


def administration_as_dips(request):
    as_config = ArchivesSpaceConfig.objects.all()[0]
    if request.POST:
        form = ArchivesSpaceConfigForm(request.POST, instance=as_config)
        if form.is_valid():
            new_asconfig = form.save()
            # save this new form data into MicroServiceChoiceReplacementDic
            settings = {
                "%host%": new_asconfig.host,
                "%port%": str(new_asconfig.port),
                "%user%": new_asconfig.user,
                "%passwd%": new_asconfig.passwd,
                "%restrictions%": new_asconfig.premis,
                "%object_type%": new_asconfig.object_type,
                "%xlink_actuate%": new_asconfig.xlink_actuate,
                "%xlink_show%": new_asconfig.xlink_show,
                "%uri_prefix%": new_asconfig.uri_prefix,
                "%access_conditions%": new_asconfig.access_conditions,
                "%use_conditions%": new_asconfig.use_conditions,
                "%use_statement%": new_asconfig.use_statement,
                "%repository%": str(new_asconfig.repository),
                "%inherit_notes%": str(new_asconfig.inherit_notes),
            }

            logger.debug('New ArchivesSpace settings: %s', (settings,))
            new_mscrDic = models.MicroServiceChoiceReplacementDic.objects.get(description='ArchivesSpace Config')
            logger.debug('Trying to save mscr %s', (new_mscrDic.description,))
            new_asconfig.save()
            logger.debug('Old: %s', (new_mscrDic.replacementdic,))
            new_mscrDic.replacementdic = str(settings)
            logger.debug('New: %s', (new_mscrDic.replacementdic,))
            new_mscrDic.save()
            logger.debug('Done')
            messages.info(request, 'Saved.')
    else:
        form = ArchivesSpaceConfigForm(instance=as_config)
    return render(request, 'administration/dips_as_edit.html', locals())

def administration_atk_dips(request):
    atk = ArchivistsToolkitConfig.objects.all()[0]
    if request.POST:
        form = ArchivistsToolkitConfigForm(request.POST, instance=atk)
        usingpass = atk.dbpass
        if form.is_valid():
            newatk = form.save()
            if newatk.dbpass != '' and newatk.dbpass != usingpass:
                usingpass = newatk.dbpass
            else:
                newatk.dbpass = usingpass

            settings = {
                "%host%": newatk.host,
                "%port%": newatk.port,
                "%dbname%": newatk.dbname,
                "%dbuser%": newatk.dbuser,
                "%dbpass%": usingpass,
                "%atuser%": newatk.atuser,
                "%restrictions%": newatk.premis,
                "%object_type%": newatk.object_type,
                "%ead_actuate%": newatk.ead_actuate,
                "%ead_show%": newatk.ead_show,
                "%use_statement%": newatk.use_statement,
                "%uri_prefix%": newatk.uri_prefix,
                "%access_conditions%": newatk.access_conditions,
                "%use_conditions%": newatk.use_conditions,
            }

            new_mscrDic = models.MicroServiceChoiceReplacementDic.objects.get(description='Archivists Toolkit Config')
            newatk.save()
            new_mscrDic.replacementdic = str(settings)
            new_mscrDic.save()


"""
