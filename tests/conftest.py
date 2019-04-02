import pytest
import os
import matcher
import openreview
import helpers.TestUtil
# from helpers.TestUtil import TestUtil

@pytest.fixture
def test_util (scope="class"):
    # or_baseurl = os.getenv('OPENREVIEW_BASEURL')
    or_baseurl = 'http://localhost:3000'
    flask_app_test_client = matcher.app.test_client()
    flask_app_test_client.testing = True
    silent = True
    test_util = helpers.TestUtil.TestUtil.get_instance(or_baseurl, flask_app_test_client, silent=silent)
    test_util.set_conf_builder(use_edge_builder=True)
    yield test_util


@pytest.fixture
def or_client (scope="class"):
    or_baseurl = 'http://localhost:3000'
    or_user = os.getenv("OPENREVIEW_USERNAME")
    or_password = os.getenv("OPENREVIEW_PASSWORD")
    client = openreview.Client(baseurl = or_baseurl)
    return client

