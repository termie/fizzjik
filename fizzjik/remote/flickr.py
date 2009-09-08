import urllib
import pprint
import mimetools
import pprint
import md5
import os

from twisted.web import client
from twisted.application import service

from fizzjik.interfaces import IRemote, implements
from fizzjik.config import ConfigurableService, if_config

import simplejson

class UploadService(ConfigurableService):
    implements(IRemote)
    base_url = "http://api.flickr.com/services/upload/"
    enabled = True

    auth_token = ""
    api_key = ""
    api_secret = ""

    @if_config('enabled')
    def startService(self):
        ConfigurableService.startService(self)
        self.test()

    def test(self):
        d = self.upload("skully.jpg", u"T\xf6st")
        d.addCallback(pprint.pprint)

    def upload(self, filename=None, title=None, desc=None, tags=None, async=1):
        params = dict(api_key=self.api_key, 
                      auth_token=self.auth_token, 
                      async=str(async))
        if title:
            params['title'] = title
        if desc:
            params['desc'] = desc
        if tags:
            params['tags'] = tags

        params['api_sig'] = self.sign(params)
        
        params['photo'] = file(filename, 'rb')

        (boundary, form) = self.multipartEncode(params)
        headers = {
            "Content-type": "multipart/form-data; boundary=%s" % boundary,
            "Content-length": str(len(form))
            }
        
        d = client.getPage(self.base_url, method="POST", headers=headers,
                           postdata=form)
        return d

    def sign(self, params):
        print params
        to_sign = [u"%s%s"%(k,params[k]) for k in sorted(params.keys())]
        print to_sign
        to_sign = self.api_secret + u"".join(to_sign)
        #print to_sign
        return md5.new(to_sign.encode('utf-8')).hexdigest()
    
    def multipartEncode(self, inputs):
        """
        Takes a dict of inputs and returns a multipart/form-data string
        containing the utf-8 encoded data. Keys must be strings, values
        can be either strings or file-like objects.
        """
        boundary = mimetools.choose_boundary()
        lines = []
        for key, val in inputs.items():
            lines.append("--" + boundary.encode("utf-8"))
            header = 'Content-Disposition: form-data; name="%s";' % key
            # Objects with name value are probably files
            if hasattr(val, 'name'):
                header += 'filename="%s";' % os.path.split(val.name)[1]
                lines.append(header)
                header = "Content-Type: application/octet-stream"
            lines.append(header)
            lines.append("")
            # If there is a read attribute, it is a file-like object, so read all the data
            if hasattr(val, 'read'):
                lines.append(val.read())
            # Otherwise just hope it is string-like and encode it to
            # UTF-8. TODO: this breaks when val is binary data.
            else:
                lines.append(val.encode('utf-8'))
        # Add final boundary.
        lines.append("--" + boundary.encode("utf-8"))
        return (boundary, '\r\n'.join(lines))

    def call(self, method, url, request, debug=0, **kw):
        if method == "GET":
            query = urllib.urlencode(request)
            url = query_string_append(url, query)
            data = None
        elif method == "POST":
            data = urllib.urlencode(request)
        if self.base_url:
            url = self.base_url + url
        
        params = dict(url=url,
                      method=method,
                      postdata=data)
        params.update(kw)
        params.setdefault("headers", {})
        if method == "POST":
            params['headers'].setdefault('Content-type', 
                                         'application/x-www-form-urlencoded')
        d = client.getPage(**params)
        if debug:
            d.addCallback(lambda x: pprint.pprint(x) and x or x)
        return d

 
def query_string_append(url, query_string):
    if url.find("?") != -1:
        sep = "&"
    else:
        sep = "?"

    return url + sep + query_string
