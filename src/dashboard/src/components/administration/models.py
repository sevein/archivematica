from django.db import models, transaction

from main.models import UUIDPkField


class ReplacementDictManager(models.Manager):
    def get_arguments(self, dictname):
        """
        Obtain a dict with all the items found in the table for a given
        dictname. The returned dict will be empty if the dictname could not
        be found.

            > ReplacementDict.objects.get_arguments('foobar')

            {u'foo': u'bar'}

        """
        return {key: value for (key, value) in self.get_queryset().filter(dictname=dictname, hidden=False).order_by('position').values_list('parameter', 'displayvalue')}

    def set_arguments(self, dictname, arguments):
        """
        Given a dictname, it persits the dictionary mapped into the table where
        each item takes its own row. It does not reuse existing values.

            > ReplacementDict.objects.set_arguments('My dictionary', {'foo': 'bar'})

        """
        if not isinstance(arguments, dict):
            return False
        with transaction.atomic():
            self.get_queryset().filter(dictname=dictname).delete()
            self.bulk_create([ReplacementDict(dictname=dictname, position=pos, parameter=parameter, displayvalue=value, hidden=False) for pos, (parameter, value) in enumerate(arguments.iteritems(), 1)])


class ReplacementDict(models.Model):
    """
    This is an extension to MicroServiceChoiceReplacementDic for local
    configuration purposes, as MicroServiceChoiceReplacementDic belongs to MCP
    and it is not mutable. MCP will look up the data in here when necessary.
    See task manager linkTaskManagerReplacementDicFromChoice for more details.
    """
    id = UUIDPkField()
    dictname = models.CharField(max_length=50)
    position = models.IntegerField(default=1)
    parameter = models.CharField(max_length=50)
    displayname = models.CharField(max_length=50)
    displayvalue = models.CharField(max_length=50)
    hidden = models.IntegerField()

    class Meta:
        db_table = u'ReplacementDict'

    objects = ReplacementDictManager()

    def __str__(self):
        return '[dict={}|pos={}] {}: {}'.format(self.dictname, self.position, self.parameter, self.displayvalue)
