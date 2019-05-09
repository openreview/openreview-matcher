import pytest
import sys
import os
import matcher
import openreview
from helpers.TestUtil import TestUtil

# sys.path.append(os.path.join(os.path.dirname(__file__), 'helpers'))

@pytest.fixture
def test_util (scope="session"):
    # or_baseurl = os.getenv('OPENREVIEW_BASEURL')
    or_baseurl = 'http://localhost:3000'
    flask_app_test_client = matcher.app.test_client()
    flask_app_test_client.testing = True
    silent = True
    test_util = TestUtil.get_instance(or_baseurl, flask_app_test_client, silent=silent)
    test_util.set_conf_builder(use_edge_builder=True)
    yield test_util


@pytest.fixture
def or_client (scope="session"):
    or_baseurl = 'http://localhost:3000'
    or_user = os.getenv("OPENREVIEW_USERNAME")
    or_password = os.getenv("OPENREVIEW_PASSWORD")
    client = openreview.Client(baseurl = or_baseurl)
    return client

