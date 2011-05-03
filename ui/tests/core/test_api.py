import json

import httplib
from mock import patch, Mock
from unittest2 import TestCase

from ..responses import response, make_identity, make_boolean, FakeResponse
from ..utils import ResourceTestCase



class CachedHttpTest(TestCase):
    def make_request(self, **kwargs):
        from tcmui.core.api import CachedHttp

        res = Mock()
        res.status = kwargs.pop("response_status", httplib.OK)
        content = kwargs.pop("response_content", "content")
        with patch(
            "tcmui.core.api.httplib2.Http.request",
            Mock(return_value=(res, content))):
            return CachedHttp().request(**kwargs)


    def test_caches_get(self):
        with patch("tcmui.core.api.cache") as cache:
            cache.get = Mock(return_value=None)

            ret = self.make_request(method="GET", uri="/uri/")

            cache.set.assert_called_with("/uri/", ret, 600)


    def _test_doesnt_cache(self, method):
        with patch("tcmui.core.api.cache") as cache:
            self.make_request(method=method, uri="/uri/")

            self.assertFalse(cache.get.called)
            self.assertFalse(cache.set.called)


    def test_put_doesnt_cache(self):
        self._test_doesnt_cache("PUT")


    def test_post_doesnt_cache(self):
        self._test_doesnt_cache("POST")


    def test_delete_doesnt_cache(self):
        self._test_doesnt_cache("DELETE")


    def test_doesnt_cache_non_OK(self):
        with patch("tcmui.core.api.cache") as cache:
            cache.get = Mock(return_value=None)

            self.make_request(method="GET", uri="/uri/", response_status=401)

            self.assertTrue(cache.get.called)
            self.assertFalse(cache.set.called)


    def test_returns_cached_for_get(self):
        with patch("tcmui.core.api.cache") as cache:
            cache.get = Mock(return_value="cached")

            ret = self.make_request(method="GET", uri="/uri/")

            cache.get.assert_called_with("/uri/")
            self.assertEqual(ret, "cached")



class TestResourceTestCase(ResourceTestCase):
    RESOURCE_DEFAULTS = {
        "name": "Default name",
        }


    def get_resource_class(self):
        from tcmui.core.api import RemoteObject, fields

        class TestResource(RemoteObject):
            name = fields.Field()
            submit_as = fields.Field(api_name="submitAs")

            def __unicode__(self):
                return u"__unicode__ of %s" % self.name

        return TestResource


    def get_resource_list_class(self):
        from tcmui.core.api import ListObject, fields

        class TestResourceList(ListObject):
            entryclass = self.resource_class
            api_name = "testresources"
            default_url = "testresources"

            entries = fields.List(fields.Object(self.resource_class))

        return TestResourceList



@patch("remoteobjects.http.userAgent")
class ResourceObjectTest(TestResourceTestCase):
    def test_get_data(self, http):
        http.request.return_value = response(
            self.make_one(name="Test TestResource"))

        c = self.resource_class.get("testresources/1", auth=self.auth)

        self.assertEqual(c.name, "Test TestResource")


    def test_unicode_conversion(self, http):
        http.request.return_value = response(
            self.make_one(name="Test TestResource"))

        c = self.resource_class.get("testresources/1", auth=self.auth)

        self.assertEqual(type(c.name), unicode)


    def test_no_id(self, http):
        c = self.resource_class(name="No id yet")
        self.assertEqual(c.id, None)


    def test_get_url(self, http):
        http.request.return_value = response(
            self.make_one(name="Test TestResource"))

        c = self.resource_class.get("testresources/1", auth=self.auth)
        c.deliver()

        self.assertEqual(
            http.request.call_args[1]["uri"],
            "http://fake.base/rest/testresources/1?_type=json")


    def test_user_agent(self, http):
        http.request.return_value = response(
            self.make_one(name="Test TestResource"))

        c = self.resource_class.get("testresources/1", auth=self.auth)
        c.deliver()

        self.assertEqual(
            http.request.call_args[1]["headers"]["user-agent"], "TCMui/0.2")


    def test_get_id(self, http):
        http.request.return_value = response(
            self.make_one(
                name="Test TestResource",
                resourceIdentity=make_identity(id="3")))

        c = self.resource_class.get("testresources/3", auth=self.auth)

        self.assertEqual(c.id, "3")


    def test_get_location(self, http):
        http.request.return_value = response(
            self.make_one(
                name="Test TestResource",
                resourceIdentity=make_identity(url="testresources/3/")))

        c = self.resource_class.get("testresources/3", auth=self.auth)
        c.deliver()

        self.assertEqual(c._location, "http://fake.base/rest/testresources/3/")


    def test_create(self, http):
        c = self.resource_class(name="Some TestResource")

        self.assertEqual(c.name, "Some TestResource")


    def test_no_auth_no_auth_headers(self, http):
        http.request.return_value = response(
            self.make_one(name="Test TestResource"))

        c = self.resource_class.get("testresources/1")
        c.deliver()

        headers = http.request.call_args[1]["headers"]
        self.assertFalse("cookie" in headers)
        self.assertFalse("authorization" in headers)


    def test_auth_headers_password(self, http):
        http.request.return_value = response(
            self.make_one(name="Test TestResource"))

        c = self.resource_class.get(
            "testresources/1",
            auth=self.creds("user@example.com", password="blah"))
        c.deliver()

        headers = http.request.call_args[1]["headers"]
        self.assertTrue("authorization" in headers)
        self.assertFalse("cookie" in headers)


    def test_auth_headers_cookie(self, http):
        http.request.return_value = response(
            self.make_one(name="Test TestResource"))

        c = self.resource_class.get(
            "testresources/1",
            auth=self.creds("user@example.com", cookie="USERTOKEN: blah"))
        c.deliver()

        headers = http.request.call_args[1]["headers"]
        self.assertFalse("authorization" in headers)
        self.assertEqual(headers["cookie"], "USERTOKEN: blah")


    def test_get_persists_auth(self, http):
        http.request.return_value = response(
            self.make_one(name="Test TestResource"))

        creds = self.creds("user@example.com", cookie="USERTOKEN: blah")

        c = self.resource_class.get("testresources/1", auth=creds)
        c.deliver()

        self.assertEqual(c.auth, creds)


    def test_persisted_auth_used(self, http):
        http.request.return_value = response(
            self.make_one(name="Test TestResource"))

        c = self.resource_class.get(
            "testresources/1",
            auth=self.creds("user@example.com", cookie="USERTOKEN: blah"))
        c.deliver()

        http.request.return_value = response(
            make_boolean(True))

        c.delete()

        headers = http.request.call_args[1]["headers"]
        self.assertEqual(headers["cookie"], "USERTOKEN: blah")


    def test_get_full_url(self, http):
        http.request.return_value = response(
            self.make_one(name="Test TestResource"))

        c = self.resource_class.get("http://some.other.url/testresources/1")
        c.deliver()

        self.assertEqual(
            http.request.call_args[1]["uri"],
            "http://some.other.url/testresources/1?_type=json")


    def test_unauthorized(self, http):
        http.request.return_value = response(
            "some error", httplib.UNAUTHORIZED, {"content-type": "text/plain"})

        c = self.resource_class.get("testresources/1", auth=self.auth)
        with self.assertRaises(self.resource_class.Unauthorized) as cm:
            c.deliver()

        self.assertEqual(
            cm.exception.args[0],
            "401  requesting TestResource "
            'http://fake.base/rest/testresources/1?_type=json: some error')


    def test_no_content(self, http):
        http.request.return_value = response(
            "", httplib.NO_CONTENT)

        c = self.resource_class.get("testresources/1", auth=self.auth)
        c.deliver()

        self.assertEqual(c.name, None)


    def test_json_error(self, http):
        http.request.return_value = response(
            {"errors":[{"error":"email.in.use"}]}, httplib.CONFLICT)

        c = self.resource_class.get("testresources/1", auth=self.auth)
        with self.assertRaises(self.resource_class.Conflict) as cm:
            c.deliver()

        self.assertEqual(
            cm.exception.args[0],
            "409  requesting TestResource "
            "http://fake.base/rest/testresources/1?_type=json: email.in.use")
        self.assertEqual(cm.exception.response_error, "email.in.use")


    def test_bad_response(self, http):
        http.request.return_value = response("Something is very wrong.", 777)

        c = self.resource_class.get("testresources/1", auth=self.auth)
        with self.assertRaises(self.resource_class.BadResponse) as cm:
            c.deliver()

        self.assertEqual(
            cm.exception.args[0],
            "Unexpected response requesting TestResource "
            "http://fake.base/rest/testresources/1?_type=json: 777 ")


    def test_missing_location_header(self, http):
        http.request.return_value = response("", 302)

        c = self.resource_class.get("testresources/1", auth=self.auth)
        with self.assertRaises(self.resource_class.BadResponse) as cm:
            c.deliver()

        self.assertEqual(
            cm.exception.args[0],
            "'Location' header missing from 302  response requesting TestResource "
            "http://fake.base/rest/testresources/1?_type=json")


    def test_bad_content_type(self, http):
        http.request.return_value = response(
            "blah", headers={"content-type": "text/plain"})

        c = self.resource_class.get("testresources/1", auth=self.auth)
        with self.assertRaises(self.resource_class.BadResponse) as cm:
            c.deliver()

        self.assertEqual(
            cm.exception.args[0],
            "Bad response fetching TestResource "
            "http://fake.base/rest/testresources/1?_type=json: "
            "content-type text/plain is not an expected type")


    def test_unicode_response(self, http):
        http.request.return_value = (
            FakeResponse(
                httplib.OK,
                headers={"content-type": "application/json"}),
            unicode(json.dumps(self.make_one(name="Test TestResource")))
            )

        c = self.resource_class.get("testresources/1", auth=self.auth)

        self.assertEqual(type(c.name), unicode)


    def test_cache_attribute(self, http):
        with patch.object(self.resource_class, "cache", True):
            with patch("remoteobjects.RemoteObject.get") as mock:
                self.resource_class.get("testresources/1", auth=self.auth)

        from tcmui.core.api import cachedUserAgent

        self.assertEqual(mock.call_args[1]["http"], cachedUserAgent)


    def test_delivered_repr(self, http):
        http.request.return_value = response(
            self.make_one(
                name="Test Thing",
                resourceIdentity=make_identity(
                    url="testresources/1")))

        c = self.resource_class.get("testresources/1", auth=self.auth)
        c.deliver()

        self.assertEqual(
            repr(c), "<TestResource: __unicode__ of Test Thing>")


    def test_undelivered_repr(self, http):
        http.request.return_value = response(
            self.make_one(
                name="Test Thing",
                resourceIdentity=make_identity(
                    url="testresources/1")))

        c = self.resource_class.get("testresources/1", auth=self.auth)

        self.assertEqual(
            repr(c), "<TestResource: testresources/1>")


    def test_filterable_fields(self, http):
        self.assertEqual(
            self.resource_class.fields.keys(),
            ["timeline", "submit_as", "name", "identity"])

        self.assertEqual(
            self.resource_class.filterable_fields().keys(),
            ["name", "submit_as"])

        # same result on second call
        self.assertEqual(
            self.resource_class.filterable_fields().keys(),
            ["name", "submit_as"])


    def test_put(self, http):
        http.request.return_value = response(
            self.make_one(
                name="Test TestResource",
                resourceIdentity=make_identity(
                    version=u"0",
                    url="testresources/1")))

        c = self.resource_class.get("testresources/1", auth=self.auth)
        c.deliver()

        http.request.return_value = response(
            self.make_one(
                name="New name",
                resourceIdentity=make_identity(
                    version=u"1",
                    url="testresources/1")))

        c.name = "New name"
        c.put()

        self.assertEqual(c.name, "New name")
        self.assertEqual(c.identity["@version"], u"1")
        request_kwargs = http.request.call_args[1]
        self.assertEqual(request_kwargs["method"], "PUT")
        self.assertEqual(
            request_kwargs["uri"],
            u"http://fake.base/rest/testresources/1?_type=json")
        self.assertEqual(
            request_kwargs["body"], "name=New+name&originalVersionId=0")
        self.assertEqual(
            request_kwargs["headers"]["content-type"],
            "application/x-www-form-urlencoded")
        self.assertEqual(
            request_kwargs["headers"]["accept"],
            "application/json")


    def test_refresh(self, http):
        http.request.return_value = response(
            self.make_one(
                name="Test TestResource",
                resourceIdentity=make_identity(
                    version=u"0",
                    url="testresources/1")))

        c = self.resource_class.get("testresources/1", auth=self.auth)
        c.deliver()

        http.request.return_value = response(
            self.make_one(
                name="New name",
                resourceIdentity=make_identity(
                    version=u"1",
                    url="testresources/1")))

        c = c.refresh()

        self.assertEqual(c.name, "New name")
        self.assertEqual(c.identity["@version"], u"1")
        request_kwargs = http.request.call_args[1]
        self.assertEqual(request_kwargs.get("method", "GET"), "GET")
        self.assertEqual(
            request_kwargs["uri"],
            u"http://fake.base/rest/testresources/1?_type=json")
        self.assertEqual(request_kwargs["headers"]["cookie"], self.auth.cookie)


    def test_delete(self, http):
        http.request.return_value = response(
            self.make_one(
                name="Test TestResource",
                resourceIdentity=make_identity(
                    url="testresources/1")))

        c = self.resource_class.get("testresources/1", auth=self.auth)
        c.deliver()

        http.request.return_value = response(
            make_boolean(True))

        c.delete()

        self.assertEqual(c.identity, None)
        self.assertEqual(c._location, None)
        request_kwargs = http.request.call_args[1]
        self.assertEqual(request_kwargs["method"], "DELETE")
        self.assertEqual(
            request_kwargs["uri"],
            u"http://fake.base/rest/testresources/1?_type=json")
        self.assertEqual(
            request_kwargs["body"], "originalVersionId=0")
        self.assertEqual(
            request_kwargs["headers"]["content-type"],
            "application/x-www-form-urlencoded")
        self.assertEqual(
            request_kwargs["headers"]["accept"],
            "application/json")

    def test_request_with_url(self, http):
        http.request.return_value = response(
            self.make_one(name="Test name"))

        c = self.resource_class.get("testresources/1")
        c._request("PUT", url="testresources/1/something")

        req = http.request.call_args[1]
        self.assertEqual(req["method"], "PUT")
        self.assertEqual(
            req["uri"],
            "http://fake.base/rest/testresources/1/something?_type=json")


    def test_request_no_location(self, http):
        c = self.resource_class()
        with self.assertRaises(ValueError):
            c._request("GET")


    def test_request_version_other_object(self, http):
        http.request.return_value = response(
            self.make_one(
                name="Test two", resourceIdentity=make_identity(
                    id=2, version=1)))
        two = self.resource_class.get("testresources/2")
        two.deliver()

        http.request.return_value = response(
            self.make_one(name="Test one"))
        one = self.resource_class.get("testresources/1")

        one._request("PUT", version_payload=two)

        req = http.request.call_args[1]
        self.assertEqual(req["body"], "originalVersionId=1")


    def test_request_no_version(self, http):
        http.request.return_value = response(
            self.make_one(name="Test one"))
        one = self.resource_class.get("testresources/1")

        one._request("PUT", version_payload=False)

        req = http.request.call_args[1]
        self.assertTrue("body" not in req)


    def test_request_json_body(self, http):
        http.request.return_value = response(
            self.make_one(name="Test one"))
        one = self.resource_class.get("testresources/1")

        one._request("PUT", default_content_type="application/json")

        req = http.request.call_args[1]
        self.assertEqual(req["body"], '{"originalVersionId": "0"}')


    def test_request_unsupported_content_type(self, http):
        http.request.return_value = response(
            self.make_one(name="Test one"))
        one = self.resource_class.get("testresources/1")

        with self.assertRaises(ValueError):
            one._request("PUT", default_content_type="text/plain")



@patch("remoteobjects.http.userAgent")
class ListObjectTest(TestResourceTestCase):
    def test_get_searchresult_empty(self, http):
        http.request.return_value = response(
            self.make_searchresult())

        c = self.resource_list_class.get(auth=self.auth)

        self.assertEqual(len(c), 0)


    def test_get_searchresult_one(self, http):
        http.request.return_value = response(
            self.make_searchresult({"name":"Test TestResource"}))

        c = self.resource_list_class.get(auth=self.auth)

        self.assertEqual(c[0].name, "Test TestResource")


    def test_get_searchresult_multiple(self, http):
        http.request.return_value = response(
            self.make_searchresult(
                {"name": "Test TestResource"},
                {"name": "Second Test"}))

        c = self.resource_list_class.get(auth=self.auth)

        self.assertEqual(c[1].name, "Second Test")


    def test_totalResults(self, http):
        http.request.return_value = response(
            self.make_searchresult(
                {"name": "Test TestResource"},
                {"name": "Second Test"}))

        c = self.resource_list_class.get(auth=self.auth)

        self.assertEqual(c.totalResults, 2)
        # test the second access, after delivery
        self.assertEqual(c.totalResults, 2)


    def test_get_array_empty(self, http):
        http.request.return_value = response(
            self.make_array())

        c = self.resource_list_class.get(auth=self.auth)

        self.assertEqual(len(c), 0)


    def test_get_array_one(self, http):
        http.request.return_value = response(
            self.make_array({"name":"Test TestResource"}))

        c = self.resource_list_class.get(auth=self.auth)

        self.assertEqual(c[0].name, "Test TestResource")


    def test_get_array_multiple(self, http):
        http.request.return_value = response(
            self.make_array(
                {"name": "Test TestResource"},
                {"name": "Second Test"}))

        c = self.resource_list_class.get(auth=self.auth)

        self.assertEqual(c[1].name, "Second Test")


    def test_get_with_url(self, http):
        http.request.return_value = response(
            self.make_array({"name":"Test TestResource"}))

        c = self.resource_list_class.get("alt-testresources/", auth=self.auth)

        self.assertEqual(c[0].name, "Test TestResource")
        self.assertEqual(
            http.request.call_args[1]["uri"],
            "http://fake.base/rest/alt-testresources/?_type=json")


    def test_get_by_id(self, http):
        http.request.return_value = response(
            self.make_one(name="Test TestResource"))

        c = self.resource_list_class.get_by_id(1, auth=self.auth)

        self.assertEqual(c.name, "Test TestResource")
        self.assertEqual(
            http.request.call_args[1]["uri"],
            "http://fake.base/rest/testresources/1?_type=json")


    def test_get_no_default_url(self, http):
        cls = self.get_resource_list_class()
        delattr(cls, "default_url")

        with self.assertRaises(ValueError):
            cls.get(auth=self.auth)


    def test_get_by_id_no_default_url(self, http):
        cls = self.get_resource_list_class()
        delattr(cls, "default_url")

        with self.assertRaises(ValueError):
            cls.get_by_id(1, auth=self.auth)


    def test_iteration_assigns_auth(self, http):
        http.request.return_value = response(
            self.make_array(
                {"name": "Test TestResource"},
                {"name": "Second Test"}))

        auth = self.auth
        c = self.resource_list_class.get(auth=auth)

        self.assertTrue(all([i.auth is auth for i in c]))


    def test_iteration_with_non_remoteobject(self, http):
        c = self.resource_list_class(entries=[1, 2])

        self.assertEqual(list(c), [1, 2])


    def test_post(self, http):
        http.request.return_value = response(
            self.make_searchresult())

        lst = self.resource_list_class.get(auth=self.auth)
        lst.deliver()

        http.request.return_value = response(
            self.make_one(name="The Thing"))

        new = self.resource_class(name="The Thing")

        lst.post(new)

        self.assertEqual(new.name, "The Thing")
        self.assertEqual(new.id, u"1")
        self.assertEqual(new.auth, self.auth)
        request_kwargs = http.request.call_args[1]
        self.assertEqual(request_kwargs["body"], "name=The+Thing")
        self.assertEqual(
            request_kwargs["uri"],
            "http://fake.base/rest/testresources?_type=json")
        self.assertEqual(request_kwargs["method"], "POST")
        headers = request_kwargs["headers"]
        self.assertEqual(headers["accept"], "application/json")
        self.assertEqual(
            headers["content-type"], "application/x-www-form-urlencoded")


    def test_post_does_not_replace_auth(self, http):
        http.request.return_value = response(
            self.make_searchresult())

        lst = self.resource_list_class.get(auth=self.auth)
        lst.deliver()

        http.request.return_value = response(
            self.make_one(name="New Thing"))

        new = self.resource_class(name="New Thing")
        new.auth = new_auth = self.creds("other@example.com", password="other")

        lst.post(new)

        self.assertEqual(new.auth, new_auth)


    def test_put(self, http):
        http.request.return_value = response(
            self.make_array(
                {"name": "Test TestResource"},
                {"name": "Second Test"}))

        lst = self.resource_list_class.get(auth=self.auth)
        lst.deliver()

        http.request.return_value = response(
            make_boolean(True))

        lst.put()

        request_kwargs = http.request.call_args[1]
        self.assertEqual(
            request_kwargs["body"], "testResourceIds=1&testResourceIds=2")


    def test_update_from_raw_list(self, http):
        c = self.resource_list_class()
        c.update_from_dict([{"ns1.name": "First"}, {"ns1.name": "Second"}])

        self.assertEqual([e.name for e in c], ["First", "Second"])


    def test_default_array_name(self, http):
        self.assertEqual(self.resource_list_class().array_name, "Testresource")


    def test_default_submit_ids_name(self, http):
        self.assertEqual(
            self.resource_list_class().submit_ids_name, "testResourceIds")


    def test_filterable_fields(self, http):
        self.assertEqual(
            self.resource_list_class.filterable_fields().keys(),
            ["name", "submit_as"])


    def test_unicode(self, http):
        c = self.resource_list_class()
        c.update_from_dict([{"ns1.name": "First"}, {"ns1.name": "Second"}])

        self.assertEqual(
            unicode(c),
            u"[<TestResource: __unicode__ of First>, "
            "<TestResource: __unicode__ of Second>]")


    def test_ours(self, http):
        cls = self.get_resource_list_class()
        with patch.object(cls, "filter") as mock_filter:
            cls.ours(auth=self.auth)

        mock_filter.assert_called_with(company=21)


    def test_paginate_noop(self, http):
        cls = self.get_resource_list_class()
        with patch.object(cls, "filter") as mock_filter:
            cls().paginate()

        mock_filter.assert_not_called()


    @patch("tcmui.core.api.pagination.DEFAULT_PAGESIZE", 10)
    def test_paginate_pagenumber(self, http):
        http.request.return_value = response(
            self.make_searchresult({"name":"Test TestResource"}))

        c = self.resource_list_class.get(auth=self.auth).paginate(
            pagenumber=2)
        c.deliver()

        req = http.request.call_args[-1]
        self.assertEqual(
            req["uri"],
            "http://fake.base/rest/testresources?_type=json&pagenumber=2&pagesize=10")


    @patch("tcmui.core.api.pagination.DEFAULT_PAGESIZE", 10)
    def test_paginate_pagesize(self, http):
        http.request.return_value = response(
            self.make_searchresult({"name":"Test TestResource"}))

        c = self.resource_list_class.get(auth=self.auth).paginate(
            pagesize=5)
        c.deliver()

        req = http.request.call_args[-1]
        self.assertEqual(
            req["uri"],
            "http://fake.base/rest/testresources?_type=json&pagenumber=1&pagesize=5")


    @patch("tcmui.core.api.pagination.DEFAULT_PAGESIZE", 10)
    def test_paginate_both(self, http):
        http.request.return_value = response(
            self.make_searchresult({"name":"Test TestResource"}))

        c = self.resource_list_class.get(auth=self.auth).paginate(
            pagesize=5, pagenumber=2)
        c.deliver()

        req = http.request.call_args[-1]
        self.assertEqual(
            req["uri"],
            "http://fake.base/rest/testresources?_type=json&pagenumber=2&pagesize=5")


    def test_sort_no_field(self, http):
        cls = self.get_resource_list_class()
        with patch.object(cls, "filter") as mock_filter:
            cls().sort(None)

        mock_filter.assert_not_called()


    def test_sort_default(self, http):
        http.request.return_value = response(
            self.make_searchresult({"name":"Test TestResource"}))

        c = self.resource_list_class.get(auth=self.auth).sort("name")
        c.deliver()

        req = http.request.call_args[-1]
        self.assertEqual(
            req["uri"],
            "http://fake.base/rest/testresources?sortfield=name&sortdirection=asc&_type=json")


    def test_sort_direction(self, http):
        http.request.return_value = response(
            self.make_searchresult({"name":"Test TestResource"}))

        c = self.resource_list_class.get(auth=self.auth).sort("name", "desc")
        c.deliver()

        req = http.request.call_args[-1]
        self.assertEqual(
            req["uri"],
            "http://fake.base/rest/testresources?sortfield=name&sortdirection=desc&_type=json")


    def test_filter(self, http):
        http.request.return_value = response(
            self.make_searchresult({"name":"Test TestResource",
                                                "submitAs": "testval"}))

        c = self.resource_list_class.get(auth=self.auth).filter(
            submit_as="testval")

        self.assertEqual(len(c), 1)
        self.assertEqual(c[0].submit_as, "testval")
        req = http.request.call_args[-1]
        self.assertEqual(
            req["uri"],
            "http://fake.base/rest/testresources?submitAs=testval&_type=json")



    def test_filter_invalid_field(self, http):
        http.request.return_value = response(
            self.make_searchresult({"name":"Test TestResource"}))

        c = self.resource_list_class.get(auth=self.auth).filter(
            submitAs="testval")

        self.assertEqual(len(c), 1)
        req = http.request.call_args[-1]
        self.assertEqual(
            req["uri"],
            "http://fake.base/rest/testresources?_type=json")



@patch("remoteobjects.http.userAgent")
class ActivatableResourceTest(ResourceTestCase):
    RESOURCE_DEFAULTS = {
        "name": "Default name",
        "active": False
        }


    def get_resource_class(self):
        from tcmui.core.api import Activatable, RemoteObject, fields

        class ActivatableResource(Activatable, RemoteObject):
            name = fields.Field()
            active = fields.Field()

            def __unicode__(self):
                return u"__unicode__ of %s" % self.name

        return ActivatableResource


    def test_activate(self, http):
        http.request.return_value = response(
            self.make_one(name="New Thing", active=False))

        a = self.resource_class.get("activatableresources/1", auth=self.auth)

        http.request.return_value = response(
            self.make_one(name="New Thing", active=True))

        a.activate()

        self.assertTrue(a.active)
        req = http.request.call_args[1]
        self.assertEqual(req["method"], "PUT")
        self.assertEqual(
            req["uri"],
            "http://fake.base/rest/activatableresources/1/activate?_type=json")



    def test_deactivate(self, http):
        http.request.return_value = response(
            self.make_one(name="New Thing", active=True))

        a = self.resource_class.get("activatableresources/1", auth=self.auth)

        http.request.return_value = response(
            self.make_one(name="New Thing", active=False))

        a.deactivate()

        self.assertFalse(a.active)
        req = http.request.call_args[1]
        self.assertEqual(req["method"], "PUT")
        self.assertEqual(
            req["uri"],
            "http://fake.base/rest/activatableresources/1/deactivate?_type=json")
