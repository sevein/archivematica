from django import forms


PREMIS_CHOICES = [('yes', 'Yes'), ('no', 'No'), ('premis', 'Base on PREMIS')]
EAD_ACTUATE_CHOICES = [('none', 'None'), ('onLoad', 'onLoad'), ('other', 'other'), ('onRequest', 'onRequest')]
EAD_SHOW_CHOICES = [('embed', 'Embed'), ('new', 'New'), ('none', 'None'), ('other', 'Other'), ('replace', 'Replace')]


class ArchivesSpaceConfigForm(forms.Form):
    host = forms.CharField(label='ArchivesSpace host', help_text='Do not include http:// or www. Example: aspace.test.org ')
    port = forms.IntegerField(label='ArchivesSpace backend port', help_text='Example: 8089')  # default=8089,
    user = forms.CharField(label='ArchivesSpace administrative user', help_text='Example: admin')
    passwd = forms.CharField(label='ArchivesSpace administrative user password', help_text='Password for user set above. Re-enter this password every time changes are made.')  # blank = true
    premis = forms.ChoiceField(choices=PREMIS_CHOICES, label='Restrictions Apply')  # default='yes'
    xlink_show = forms.ChoiceField(choices=EAD_SHOW_CHOICES, label='XLink Show')  # , default='embed'
    xlink_actuate = forms.ChoiceField(choices=EAD_ACTUATE_CHOICES, label='XLink Actuate')  # , default='none'
    object_type = forms.CharField(label='Object type', help_text='Optional, must come from ArchivesSpace controlled list. Example: sound_recording')  # blank=true
    use_statement = forms.CharField(label='Use statement', help_text='Optional, but if present should come from ArchivesSpace controlled list. Example: image-master')  # blank=True
    uri_prefix = forms.CharField(label='URL prefix', help_text='URL of DIP object server as you wish to appear in ArchivesSpace record. Example: http://example.com')
    access_conditions = forms.CharField(label='Conditions governing access', help_text='Populates Conditions governing access note')  # blank=True
    use_conditions = forms.CharField(label='Conditions governing use', help_text='Populates Conditions governing use note')  #  blank=True,
    repository = forms.IntegerField(label='ArchivesSpace repository number', help_text='Default for single repository installation is 2')  # default=2
    inherit_notes = forms.BooleanField(label='Inherit digital object notes from the parent component')  # default=False


class ArchivistsToolkitConfigForm(forms.Form):
    host = forms.CharField(required=True, label='Database Host')
    port = forms.IntegerField(required=True, label='Database Port')  # default=3306,
    dbname = forms.CharField(required=True, label='Database Name')
    dbuser = forms.CharField(required=True, label='Database User')
    dbpass = forms.CharField(required=True, label='Database Password')
    atuser = forms.CharField(required=True, label='Archivists Toolkit Username')
    premis = forms.ChoiceField(required=True, choices=PREMIS_CHOICES, label='Restrictions Apply')  # default='yes'
    ead_actuate = forms.ChoiceField(required=True, choices=EAD_ACTUATE_CHOICES, label='EAD DAO Actuate')  # default='none'
    ead_show = forms.ChoiceField(required=True, choices=EAD_SHOW_CHOICES, label='EAD DAO Show')  # default='embed'
    object_type = forms.CharField(required=True, label='Object type')
    use_statement = forms.CharField(required=True, label='Use Statement')
    uri_prefix = forms.CharField(required=True, label='URL prefix')
    access_conditions = forms.CharField(required=True, label='Conditions governing access')
    use_conditions = forms.CharField(required=True, label='Conditions governing use')


class AtomConfigForm(forms.Form):
    url = forms.CharField(required=True, label='Upload URL', help_text='URL where the Qubit index.php frontend lives, SWORD services path will be appended.')
    email = forms.CharField(required=True, label='Login email', help_text='E-mail account used to log into Qubit.')
    password = forms.CharField(required=True, label='Login password', help_text='E-mail account used to log into Qubit.')
    version = forms.ChoiceField(label='AtoM version', choices=((1, '1.x'), (2, '2.x')))
    rsync_target = forms.CharField(required=False, label='Rsync target', help_text='The DIP can be sent with Rsync to a remote host before is deposited in Qubit. This is the destination value passed to Rsync (see man 1 rsync). For example: foobar.com:~/dips/.')
    rsync_command = forms.CharField(required=False, label='Rsync command', help_text='If --rsync-target is used, you can use this argument to specify the remote shell manually. For example: ssh -p 22222 -l user.')
    debug = forms.ChoiceField(required=False, label='Debug mode', help_text='Show additional details.', choices=((False, 'No'), (True, 'Yes')))
    key = forms.CharField(required=False, label='REST API key', help_text='Used in metadata-only DIP upload.')
