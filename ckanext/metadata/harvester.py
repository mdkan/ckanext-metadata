'''Harvester module for the universal metadata harvester of CKAN.
'''
import urllib2
import json
import jsonpickle


from ckanext.harvest.harvesters.base import HarvesterBase
from ckanext.harvest.model import HarvestObject
from ckanext.oaipmh.harvester import OAIPMHHarvester
from ckanext.ddi.harvester import DDIHarvester

from oaipmh.metadata import MetadataRegistry, oai_dc_reader
from oaipmh.error import XMLSyntaxError
import oaipmh.client


class MetadataHarvester(HarvesterBase):
    config = None
    harvester = None

    def __init__(self):
        self.harvester = None

    def info(self):
        return {
            'name': 'Metadata',
            'title': 'Metadata harvester',
            'description': 'Universal metadata harvester for various formats',
            }

    def gather_stage(self, harvest_job):
        url = harvest_job.source.url
        # Test wether we should use OAI-PMH or DDI
        metadata_registry = MetadataRegistry()
        metadata_registry.registerReader('oai_dc', oai_dc_reader)
        client = oaipmh.client.Client(url, metadata_registry)
        try:
            client.identify()
        except XMLSyntaxError:
            self.harvester = DDIHarvester()
        except urllib2.URLError:
            self._save_gather_error('Could not identify source!', harvest_job)
            return None
        if not self.harvester:
            self.harvester = OAIPMHHarvester()
        objs = self.harvester.gather_stage(harvest_job)
        ret = []
        for obj in objs:
            obj = HarvestObject.get(obj)
            cont = obj.content
            dict = json.loads(cont)
            dict['harv'] = jsonpickle.encode(self.harvester)
            obj.content = json.dumps(dict)
            obj.save()
            ret.append(obj.id)
        return ret

    def fetch_stage(self, harvest_object):
        harv = jsonpickle.decode(json.loads(harvest_object.content)['harv'])
        self.harvester = harv
        bool = self.harvester.fetch_stage(harvest_object)
        cont = harvest_object.content
        dict = json.loads(cont)
        dict['harv'] = jsonpickle.encode(self.harvester)
        harvest_object.content = json.dumps(dict)
        harvest_object.save()
        return bool

    def import_stage(self, harvest_object):
        harv = jsonpickle.decode(json.loads(harvest_object.content)['harv'])
        self.harvester = harv
        return self.harvester.import_stage(harvest_object)
