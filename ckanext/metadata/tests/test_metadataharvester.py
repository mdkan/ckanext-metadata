'''Tests for universal harvester.
'''
import unittest
import mock
import urllib2
from StringIO import StringIO

from ckan.tests.functional.base import FunctionalTestCase
from ckan.tests import CreateTestData
from ckan.model import Session

from ckanext.metadata.harvester import MetadataHarvester
from ckanext.harvest.model import HarvestJob, HarvestObject, HarvestSource,\
                                    setup

from ckanext.oaipmh.oaipmh_server import CKANServer
from ckanext.oaipmh.harvester import OAIPMHHarvester

from ckanext.ddi.harvester import DDIHarvester

from oaipmh.server import BatchingServer, oai_dc_writer
from oaipmh.client import ServerClient
from oaipmh.metadata import oai_dc_reader
from oaipmh import metadata

import oaipmh

import testdata

realopen = urllib2.urlopen


class TestUniversalHarvester(unittest.TestCase, FunctionalTestCase):

    num_side_effect = 1
    gathered = None
    harv = None

    @classmethod
    def setup_class(self):
        CreateTestData.create()
        setup()

    @classmethod
    def teardown_class(self):
        Session.remove()

    def test_harvester(self):
        harv = MetadataHarvester()
        self.assert_(harv)
        self.assert_(isinstance(harv.info(), dict))

    def test_0harvester_url_error(self):
        self.harv = MetadataHarvester()
        self.harv.config = "{}"
        harvest_job = HarvestJob()
        harvest_job.source = HarvestSource()
        harvest_job.source.title = "Test"
        harvest_job.source.url = "http://foo"
        harvest_job.source.type = "Metadata"
        urllib2.urlopen = realopen
        self.assert_(self.harv.gather_stage(harvest_job) == None)

    def _side_effect_ddi_datas(self, foo):
        if self.num_side_effect == 1:
            self.num_side_effect = 2
            return StringIO(testdata.test_ddi_data)
        if self.num_side_effect == 2:
            self.num_side_effect = 1
            return StringIO(testdata.test_ddi_data)

    def test_harvester_1gather_ddi(self):
        self.harv = MetadataHarvester()
        self.harv.config = "{}"
        harvest_job = HarvestJob()
        harvest_job.source = HarvestSource()
        harvest_job.source.title = "Test"
        harvest_job.source.url = "http://foo"
        harvest_job.source.type = "Metadata"
        urllib2.urlopen = mock.Mock(side_effect=self._side_effect_ddi_datas)
        self.gathered = self.harv.gather_stage(harvest_job)
        self.assert_(len(self.gathered) == 1)
        self.assert_(isinstance(self.harv.harvester, DDIHarvester))

    def test_harvester_2fetch_ddi(self):
        self.test_harvester_1gather_ddi()
        harvobj = HarvestObject.get(self.gathered[0])
        urllib2.urlopen = mock.Mock(return_value=StringIO(testdata.test_ddi_xml))
        self.assert_(self.harv.fetch_stage(harvobj))

    def test_harvester_3import_ddi(self):
        self.test_harvester_1gather_ddi()
        self.test_harvester_2fetch_ddi()
        harvest_object = HarvestObject.get(self.gathered[0])
        self.assert_(self.harv.import_stage(harvest_object))

    def test_harvester_4gather_oaipmh(self):
        self.harv = MetadataHarvester()
        self.harv.config = "{}"
        harvest_job = HarvestJob()
        harvest_job.source = HarvestSource()
        harvest_job.source.title = "Test"
        harvest_job.source.url = "http://foo"
        harvest_job.source.type = "Metadata"
        client = CKANServer()
        metadata_registry = metadata.MetadataRegistry()
        metadata_registry.registerReader('oai_dc', oai_dc_reader)
        metadata_registry.registerWriter('oai_dc', oai_dc_writer)
        serv = BatchingServer(client, metadata_registry=metadata_registry)
        oaipmh.client.Client = mock.Mock(return_value=ServerClient(serv, metadata_registry))
        self.gathered = self.harv.gather_stage(harvest_job)
        self.assert_(len(self.gathered) > 1)
        self.assert_(isinstance(self.harv.harvester, OAIPMHHarvester))

    def test_harvester_5fetch_oaipmh(self):
        self.test_harvester_4gather_oaipmh()
        harvest_object = HarvestObject.get(self.gathered[0])
        self.assert_(self.harv.fetch_stage(harvest_object))

    def test_harvester_6import_oaipmh(self):
        self.test_harvester_4gather_oaipmh()
        self.test_harvester_5fetch_oaipmh()
        harvest_object = HarvestObject.get(self.gathered[0])
        self.assert_(self.harv.import_stage(harvest_object))
