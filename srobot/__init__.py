#!/usr/bin/python
#coding=utf-8
#Copyright (c) 2013, Yu Renbi
#All rights reserved.
#Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
#Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
#Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
#THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS 'AS IS' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
from bs4 import BeautifulSoup
import mechanize
import urllib
import urllib2
import urlparse
import svcode
import time
import functools

UA_GGBOT = r"Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
UA_IE9 = r"Mozilla/5.0 (Windows; U; MSIE 9.0; Windows NT 9.0; zh-CN)"
HEADERS = [('User-agent', UA_IE9)]
HEADER_XMLHTTPREQUEST = HEADERS[:]
HEADER_XMLHTTPREQUEST.append( ('X-Requested-With', 'XMLHttpRequest') )

def loop_for_urlerror(times=3):
    def dec(func):
        @functools.wraps(func)
        def rfunc(*args, **kargs):
            looptimes = 0
            while 1:
                try:
                    return func(*args, **kargs)
                except urllib2.URLError:
                    if looptimes < 3:
                        looptimes += 1
                        time.sleep(1)
                        continue
                    else:
                        raise
        return rfunc
    return dec

def query2dict(query):
    rdict = {}
    for s in query.split("&"):
        name, value = s.split("=")
        rdict[name] = value
    return rdict

class Page(object):
    def __init__(self, url, pin_gdata = None, ajax = False):
        self.url = url
        self.ajax = ajax

        query = urlparse.urlparse("url").query
        if query:
            dquery = query2dict(query)
            if not pin_gdata:
                pin_gdata = dquery
            else:
                pin_gdata.update(dquery)

        self.browser = None
        self.pre_response = None
        self.url = self.url + "?" + urllib.urlencode(pin_gdata) if pin_gdata else self.url
        self._pin_gdata = pin_gdata

    @loop_for_urlerror(3)
    def refresh(self, gdata = None, data = None):
        """Refresh the url. g(et)data and data are dict."""
        if self.ajax:
            self.browser.addheaders = HEADER_XMLHTTPREQUEST

        if self._pin_gdata:
            url = self.url + "&" + urllib.urlencode(gdata) if gdata else self.url
        else:
            url = self.url + "?" + urllib.urlencode(gdata) if gdata else self.url
        if not data:
            self.pre_response = self.browser.open(url)
        else:
            self.pre_response = self.browser.open(url, urllib.urlencode(data))
        self.raw_response_content = self.pre_response.read()
        self.soup = BeautifulSoup(self.raw_response_content)
        self.browser.addheaders = HEADERS
        return self.soup

    def get_form(self, *args, **kargs):
        if "nr" in kargs:
            self.browser.select_form(nr=int(kargs["nr"]))
        else:
            formsoup = self.soup.find_all(*args, **kargs)[0]
            self.browser.select_form(name=formsoup.attrs["name"])
        return self.browser.form

class LoginPage(Page):
    def __init__(self, url, urlvcode, judgelogin = lambda raw_page: "用户名" not in raw_page, judgevcode = lambda raw_page: "验证码错误" not in raw_page,
                                    pin_gdata = None, pin_gdata_vcode = None, ajax = False, *args, **kargs):
        super(LoginPage, self).__init__(url, pin_gdata, ajax)
        self.urlvcode = urlvcode
        self.urlvcode = self.urlvcode + "?" + urllib.urlencode(pin_gdata_vcode) if pin_gdata_vcode else self.urlvcode
        self.form = None
        self._args = args
        self._kargs = kargs
        self.judgelogin = judgelogin
        self.judgevcode = judgevcode

    @loop_for_urlerror(3)
    def login(self, formdata, vcodename, gdata = None, data = None):
        @loop_for_urlerror(3)
        def get_vcode():
            r = self.browser.open(self.urlvcode)
            isuffix = r.info().dict.get("content-type", "image/jpg")
            isuffix = "." + isuffix.split("/")[1]
            raw_image = r.read()
            svcode.show_vcode(raw_image, isuffix)
            return raw_input("CAPTCHA: ")

        self.refresh(gdata, data)
        if not self.form:
            self.form = self.get_form(*self._args, **self._kargs)
        
        raw_page = ""
        firstflag = True
        while not self.judgevcode(raw_page) or not raw_page:
            if not firstflag:
                print "上一次验证码输入错误, 请再输入一遍"
            else:
                firstflag = False
            vcode = get_vcode()
            self.refresh(gdata, data)
            for k, v in formdata.iteritems():
                self.form[k] = v
            self.form[vcodename] = vcode
            self.browser.form = self.form
            raw_page = self.browser.submit().read()

        if self.judgelogin(raw_page):
            self.raw_response_content = raw_page
            self.soup = BeautifulSoup(raw_page)
            return True
        else:
            return False

class Site(object):
    def __init__(self, baseurl):
        self.baseurl = baseurl
        self.pages = {}
        browser = mechanize.Browser()
        #browser.set_debug_http(True)
        #browser.set_debug_responses(True)
        browser.set_handle_referer(True)
        browser.set_handle_robots(False)
        browser.set_handle_redirect(True)
        browser.addheaders = HEADERS
        self.browser = browser

    def addpage(self, name, *args, **kargs):
        args = list(args)
        if "url" not in kargs:
            args[0] = urlparse.urljoin(self.baseurl, args[0])
        else:
            kargs["url"] = urlparse.urljoin(self.baseurl, kargs["url"])
        page = Page(*args, **kargs)
        page.browser = self.browser
        self.pages[name] = page

    def addloginpage(self, name, *args, **kargs):
        args = list(args)
        if "url" not in kargs:
            args[0] = urlparse.urljoin(self.baseurl, args[0])
        else:
            kargs["url"] = urlparse.urljoin(self.baseurl, kargs["url"])
        if "urlvcode" not in kargs:
            args[1] = urlparse.urljoin(self.baseurl, args[1])
        else:
            kargs["urlvcode"] = urlparse.urljoin(self.baseurl, kargs["urlvcode"])

        page = LoginPage(*args, **kargs)
        page.browser = self.browser
        self.pages[name] = page

    def refresh(self, _name, *args, **kargs):
        return self.pages[_name].refresh(*args, **kargs)

    def get_form(self, name_, *args, **kargs):
        return self.pages[name_].get_form(*args, **kargs)

    def last_raw(self, name):
        return self.pages[name].raw_response_content

    def last_soup(self, name):
        return self.pages[name].soup.prettify()


#TODO: write a better wrapper for forms
#class Form(Page):
    #def __init__(self, baseurl, formsoup):
        #self.method = form.attrs.get("method", "POST").upper()
        #url = form.attrs.get("action", "./")
        #self.default_data = {}
        #for tag in formsoup.find_all("input"):
            #self.default_data[tag.name] = tag.value
        #super(Form, self).__init__(urlparse.urljoin(baseurl, url))

    #def submit(data, gdata)

def main():
    """just some simple uncomplete tests"""

    try:
        import mysensitive
        USERNAME = mysensitive.username
        PASSWORD = mysensitive.password
    except ImportError:
        USERNAME = raw_input("username: ")
        PASSWORD = raw_input("password: ")

    site = Site("http://www.baidu.com")
    site.addpage("home", url="/")
    site.refresh("home")
    print site.last_raw("home")
    print "================================================================\n\n\n"
    print site.last_soup("home")
    print site.get_form("home", name="form")

    print "================================================================\n\n\n"
    cjsite = Site("http://cj.shu.edu.cn")
    cjsite.addloginpage("login",  "/", "/User/GetValidateCode?%20%20+%20GetTimestamp()", 
                            judgevcode=lambda rawpage: "验证码不正确" not in rawpage, nr=0)
    cjsite.addpage("grade", url="/StudentPortal/CtrlScoreQuery", ajax=True)
    print cjsite.pages["login"].login(dict(txtUserNo=USERNAME, txtPassword=PASSWORD), "txtValidateCode")
    cjsite.pages["grade"].refresh(data=dict(academicTermID="9"))
    print cjsite.last_raw("grade")

if __name__ == '__main__':
    main()
