from __future__ import annotations
from typing import (
    Generator,
    Optional,
    Union,
    NewType
)
from PIL import Image
from requests import Session
from bs4 import BeautifulSoup
from .utils import txt2json
from io import (
    TextIOWrapper,
    StringIO
)
from io import (
    BufferedReader,
    BytesIO
)
import re

class InvalidEmailORPass(Exception):
    pass

class UserNotLoggin(Exception):
    pass

class InvalidID(Exception):
    pass

class FacebookError(Exception):
    pass

class Checkpoint(Exception):
    pass

class FacebookBase(Session):
    headers: dict[str, str]
    BASE_URL = 'https://mbasic.facebook.com'
    def __init__(self, cookiefile: Optional[str] = None) -> None:
        super().__init__()
        self.headers = {
            'accept-language': 'en-US,en;q=0.9',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "Linux",
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "none",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.60 Safari/537.36"
        }
        self.cookiefile = cookiefile
        if cookiefile:
            self.load_cookie(cookiefile)
    @classmethod
    def endpoint(cls, endp: str):
        return cls.BASE_URL.rstrip() + '/' + endp.lstrip()

    @property
    def get_name(self):
        status = self.get(self.endpoint('profile.php')).text
        t = BeautifulSoup(status, 'html.parser').title
        if t:
            return t.text
        
    def load_cookie(self, file: str):
        for cookie in txt2json(open(file,'r').read()):
            cookie: dict[str,str]
            self.cookies.set(**cookie)

    def dump(self):
        if self.cookiefile:
            self.dumps(open(self.cookiefile, 'w'))

    def dumps(self, buf: Union[TextIOWrapper, StringIO]):
        buf.write('#Generated using FBPy\n')
        for c in self.cookies:
            buf.write('\t'.join(map(str, [
                c.domain,
                ['FALSE', 'TRUE'][c.domain_initial_dot],
                c.path, ['FALSE', 'TRUE'][c.secure],
                c.expires if not c.expires == None else 0,
                c.name,
                c.value
            ]))+'\n')

    def login(self, email: str, password: str):
        st = self.get(self.endpoint('login'))
        html=st.text
        post = dict((*re.findall(r'name="([\w]+)" value="([\w]+)"', html), ('login', 'Log In'), ('email', email), ('pass', password)))
        resp = self.post(self.endpoint(re.findall(r'action="(/[\w&-_=]+)"',html)[0].replace('amp;','')), data=post).text
        bs = BeautifulSoup(resp, 'html.parser')
        title = (bs.title.text if bs.title else '').lower()
        if bs.find_all('div', attrs={'id': 'login_error'}) or ('error' in title or 'log in' in title or 'find your' in title):
            if 'error' in title:
                raise FacebookError()
            elif 'find your' in title:
                return self.login(re.findall(r'/([\w.]+)\?', self.get(self.endpoint(email)).url)[0], password)
            raise InvalidEmailORPass('check your email & password')
        elif 'checkpoint' in resp.lower():
            raise Checkpoint()
class FriendRequest:
    def __init__(self, name: str, confirm: str, delete: str, session: Facebook) -> None:
        self.name = name
        self.confirm_url = confirm
        self.delete_url = delete
        self.session =  session
        self.id = re.findall(r'confirm=([0-9]+)', confirm)[0]
    def confirm(self):
        self.session.get(self.confirm_url)
        for i in filter(lambda x:x.id == self.id, self.session.friend_request()):
            return True
        return False
    def delete(self):
        self.session.get(self.delete_url)
        for i in filter(lambda x:x.id == self.id, self.session.friend_request()):
            return True
        return False
    def __repr__(self) -> str:
        return self.name
class Message:
    pass


class TextMessage(Message):
    def __init__(self, msg: str) -> None:
        self.msg = msg

class MediaMessage(TextMessage):
    def __init__(self, msg: str, media_url: str) -> None:
        super().__init__(msg)
        self.url = media_url
    def download(self):
        pass

class Friend:
    def __init__(self, add: str, requests: FacebookBase = FacebookBase(), name: Optional[str] = None) -> None:
        self.id = re.findall(r'\?id=([0-9]+)', add)[0]
        self.name = name
        self.add_friend = add.replace('amp;','')
        self.request = requests
    def add(self):
        return self.request.get(self.request.endpoint(self.add_friend))

    def friends(self) -> Generator[Friend, None, None]:
        resp = self.request.get(self.request.endpoint('profile.php'), params={'id': self.id, 'v':'friends'}).text
        while True:
            bs = BeautifulSoup(resp, 'html.parser').find_all('div', attrs={'id':'m_more_friends'})
            yield from [self.__class__(iP, self.request, u) for u, iP in zip(
                        [i.text for i in BeautifulSoup(resp, 'html.parser').find_all('a', attrs={'class':'ce'})],
                        re.findall(r'\"(/[\w/]+add_fr[.\w_&%/\-=;?]+)\"',resp)
                        )]
            if bs:
                resp = self.request.get(self.request.endpoint(bs[0].a['href'])).text
            else:
                break
    def __repr__(self) -> str:
        return f'name: {self.name} ID: {self.id}'
class FriendMessage:
    def __init__(self, session: Facebook, url: str, last_message: str, isread: bool, name: str) -> None:
        self.name = name
        self.session = session
        self.url = session.endpoint(url.lstrip())
        self.isread = isread
        self.last_message = last_message
    def fetchall_message(self):
        pass
    def send_text(self, text: str):
        resp = BeautifulSoup(self.session.get(self.url).text, 'html.parser').find_all('form')[1]
        self.session.headers['referer'] = self.url
        data = dict([(i['name'], i.get('value','')) for i in resp.find_all('input')])
        data.pop('like')
        data.pop('send_photo')
        data.update({'body': text})
        return self.session.post(FacebookBase.endpoint(resp['action']), data=data)

    def send_like(self):
        resp = BeautifulSoup(self.session.get(self.url).text, 'html.parser').find_all('form')[1]
        self.session.headers['referer'] = self.url
        data = dict([(i['name'], i.get('value','')) for i in resp.find_all('input')])
        data.pop('send_photo')
        data.update({'like':'Like'})
        return self.session.post(FacebookBase.endpoint(resp['action']), data=data)

    def send_photo(self, files: list[str], text: str = ''):
        resp = BeautifulSoup(self.session.get(self.url).text, 'html.parser').find_all('form')[1]
        self.session.headers['referer'] = self.url
        data = dict([(i['name'], i.get('value','')) for i in resp.find_all('input')])
        data.pop('like')
        data.update({'send_photo':'Add Photos'})
        ph = self.session.post(FacebookBase.endpoint(resp['action']), data=data).text
        data = dict([(i['name'], i['value']) for i in BeautifulSoup(ph, 'html.parser').find_all('input', attrs={'type':'hidden'})])
        data.update({'body':text})
        f = {n: ('a.jpg', open(i, 'rb')) for i,n in zip(files, ['file1', 'file2', 'file3'])}
        if f.__len__() < 3:
            f.update({'file'+(i+1).__str__(): ('b.jpg', b'') for i in range(f.__len__(), 3)})
        return self.session.post('https://upload.facebook.com/_mupload_/mbasic/messages/attachment/photo/', data=data, files=f)


    def __repr__(self) -> str:
        return f"<name: {self.name}  msg:'{self.last_message}' read:{self.isread}>"

class Facebook(FacebookBase):
    def __init__(self, cookiefile:Optional[str] = None):
        super().__init__(cookiefile)

    @property
    def profile(self):
        return self.get(self.endpoint('profile.php'))
    
    def search_people(self, name: str) -> Generator[Friend, None, None]:
        resp = self.get(self.endpoint('search/people/'), params={'q': name, 'source':'filter', 'isTrending':0}).text
        while True:
            try:
                bs = BeautifulSoup(resp, 'html.parser').find_all('div', attrs={'id':'see_more_pager'})
                yield from [Friend(iP, self, u) for u, iP in zip(
                    [i.text for i in BeautifulSoup(resp, 'html.parser').find_all('div', attrs={'class':'ce'})],
                    re.findall(r'\"(/[\w/]+add_fr[.\w_&%/\-=;?]+)\"',resp)
                    )]
                if bs:
                    resp = self.get(bs[0].a['href']).text
                else:
                    break
            except Exception:
                break
    def messages(self):
        x = []
        for i in BeautifulSoup(self.get(self.endpoint('messages')).text, 'html.parser').find_all('td', attrs={'aria-hidden':'false'}):
            h3 = i.find_all('h3')
            x.append(FriendMessage(self, h3[0].a['href'], h3[1].span.text, h3[0]['class'][1] == 'ba', h3[0].text))
        return x

    def new_message(self, ids: list[str], text:  str, image: list[str] = []):
        resp = self.get(self.endpoint('messages/compose'), params = {f'ids[{n}]': d for n, d in enumerate(ids)})
        form = BeautifulSoup(resp.text, 'html.parser').find_all('form')
        hdata = {x['name']: x['value'] for x in form[1].find_all('input')}
        hdata.update({'body': text})
        if image:
            f = {n: ('a.jpg', open(i, 'rb')) for i,n in zip(image, ['file1', 'file2', 'file3'])}
            if f.__len__() < 3:
                f.update({'file'+(i+1).__str__(): ('b.jpg', b'') for i in range(f.__len__(), 3)})
            return self.post(form[2]['action'], data=hdata, files=f)
        else:
            assert text
            return self.post(self.endpoint('messages/send'), params={'icm':1}, data=hdata)

    def friend_request(self):
        resp = self.get(self.endpoint('/friends/center/requests/')).text
        url = [i[0].replace('amp;','') for i in re.findall(r'([\w/.?]+(confirm|delete)=[\w%&;-=_.]+)', resp)]
        return [ FriendRequest(n, self.endpoint(c), self.endpoint(d), self) for n, c, d in zip(re.findall(r'\?uid=[\w%_&=;.]+">([^<]+)', resp),url[::2], url[1::2])]


