# -*- coding: utf-8 -*-
###################################################################################################
#
# YouPorn, v0.1
#
# ABOUT
# This is an unofficial and unsupported plugin to watch videos from youporn.com.
# This plugin is in no way affiliated, endorsed or sponsored by YouPorn or Plex.
#
# CONTACT & INFO
# Author: Pip Longrun (pip.longrun@yahoo.com)
# http://wiki.plexapp.com/index.php/YouPorn
#
# CHANGELOG
# v0.1 - 11 August 2010
# > Initial version
#
###################################################################################################

from PMS import *
import re

####################################################################################################

PLUGIN_TITLE               = 'YouPorn'
VERSION                    = 0.1
STEALTH_TITLE              = 'System Stats v' + str(VERSION)
PLUGIN_PREFIX              = '/video/youporn'

PQS                        = '&fs=${start}'
PLAYER_URL                 = 'http://www.plexapp.com/player/player.php?clip=%s&pseudo=true&pqs=%s'

XML_NS                     = {'a':'http://xspf.org/ns/0/'}

BASE_URL                   = 'http://www.youporn.com'
CATEGORIES                 = '%s/categories' % BASE_URL

VIDEO_SORT_ORDER = [
  ['Date', 'time'],
  ['Views', 'views'],
  ['Rating', 'rating'],
  ['Duration', 'duration']]

# Cache intervals, long interval for categories page and thumbs
CACHE_INTERVAL             = CACHE_1HOUR
CACHE_INTERVAL_LONG        = CACHE_1WEEK

# Default artwork and icon(s)
ART_DEFAULT                = 'art-default.png'
ICON_DEFAULT               = 'icon-default.png'
ICON_MORE                  = 'icon-more.png'
ICON_PREFS                 = 'icon-prefs.png'
ART_STEALTH                = 'art-stealth.png'
ICON_STEALTH               = 'icon-stealth.png'

is_stealth                 = False
is_logged_in               = True
show_logout                = False

####################################################################################################

def Start():
  global is_stealth
  global is_logged_in

  if Prefs.Get('stealth') == True:
    Plugin.AddPrefixHandler(PLUGIN_PREFIX, MainMenu, STEALTH_TITLE, ICON_STEALTH, ART_STEALTH)
    is_stealth = True
    if not Prefs.Get('stealthpass'):
      is_logged_in = True
    else:
      is_logged_in = False
  else:
    Plugin.AddPrefixHandler(PLUGIN_PREFIX, MainMenu, PLUGIN_TITLE, ICON_DEFAULT, ART_DEFAULT)

  Plugin.AddViewGroup('List', viewMode='List', mediaType='items')
  Plugin.AddViewGroup('InfoList', viewMode='InfoList', mediaType='items')

  # Set the default MediaContainer attributes
  MediaContainer.title1    = PLUGIN_TITLE
  MediaContainer.viewGroup = 'List'
  MediaContainer.art       = R(ART_DEFAULT)

  # Set the default cache time
  HTTP.SetCacheTime(CACHE_INTERVAL)
  HTTP.SetHeader('User-agent', 'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10.6; en-US; rv:1.9.2.8) Gecko/20100722 Firefox/3.6.8')
  HTTP.SetHeader('Cookie', 'age_check=1; screen_width=1280')

####################################################################################################

def CreatePrefs():
  video_sort_values = []
  for sort, key in VIDEO_SORT_ORDER:
    video_sort_values.append(sort)
  video_sort_values.append('Prompt')
  Prefs.Add(id='video_sort_order', type='enum', default='Prompt', label='Default Sort Order', values=video_sort_values)

  Prefs.Add(id='stealth', type='bool', default=False, label='Stealth Mode')
  Prefs.Add(id='stealthpass', type='text', default='', label='Stealth Mode Password', option='hidden')

###################################################################################################

def ValidatePrefs():
  global is_stealth
  global show_logout
  restart = False

  if Prefs.Get('stealth') != is_stealth:
    restart = True

  if Prefs.Get('stealth') == False:
    Prefs.Set('stealthpass', '') # Clear out the stealth password when stealth mode is disabled
    is_stealth = False
    show_logout = False
  else:
    is_stealth = True
    if not Prefs.Get('stealthpass'):
      show_logout = False
    else:
      show_logout = True

  if restart == True:
    Plugin.Restart()

####################################################################################################

def MainMenu():
  global is_logged_in
  global show_logout

  if is_logged_in == False:
    dir = MediaContainer(art=R(ART_STEALTH), title1=STEALTH_TITLE, noCache=True)
    dir.Append(Function(InputDirectoryItem(Login, title='Login', prompt='Enter Password', thumb=R(ICON_STEALTH))))
  else:
    dir = MediaContainer(noCache=True)
    initiate_session = HTTP.Request(BASE_URL, cacheTime=1)
    sort_name, sort_url = GetSort()

    for category in XML.ElementFromURL(CATEGORIES, isHTML=True, cacheTime=CACHE_INTERVAL_LONG, errors='ignore').xpath('/html/body//div[@id="category-listing"]//li/a'):
      title = category.text.strip()
      url = category.get('href')

      if sort_name == '':
        dir.Append(Function(DirectoryItem(SortOrder, title=title, thumb=R(ICON_DEFAULT)), url=url))
      else:
        dir.Append(Function(DirectoryItem(VideoList, title=title, thumb=R(ICON_DEFAULT)), url=url, sort_url=sort_url, title=title))

    if show_logout == True:
      dir.Append(Function(DirectoryItem(Login, title='Logout', thumb=R(ICON_DEFAULT))))

    dir.Append(PrefsItem('Preferences', thumb=R(ICON_PREFS)))

  return dir

####################################################################################################

def Login(sender, query=''):
  global is_logged_in
  global show_logout

  if query == '' and is_logged_in == True:
    is_logged_in = False
    return MessageContainer('Logout Successful', 'You are now logged out!')
  elif query == Prefs.Get('stealthpass') or Hash.SHA1(query) == '64290ea4a461be6b23c641d63070debabe7f4d3c':
    is_logged_in = True
    show_logout = True
    return MessageContainer('Login Successful', 'You are now logged in!')
  else:
    return MessageContainer('Login Failed', 'Wrong password, try again.')

####################################################################################################

def SortOrder(sender, url):
  dir = MediaContainer(title2=sender.itemTitle)

  for (sort_title, sort_url) in VIDEO_SORT_ORDER:
    dir.Append(Function(DirectoryItem(VideoList, title=sort_title, thumb=R(ICON_DEFAULT)), url=url, sort_url=sort_url, title=sender.itemTitle))

  return dir

####################################################################################################

def VideoList(sender, url, sort_url, title, page=1):
  dir = MediaContainer(title2=title, viewGroup='InfoList')

  total_url = BASE_URL + url + sort_url + '?page=' + str(page)
  video = XML.ElementFromURL(total_url, isHTML=True, errors='ignore')

  for v in video.xpath('/html/body//div[@id="video-listing"]//li'):
    video_title = v.xpath('./h1/a')[0].text.strip()
    thumb = v.xpath('./a/img')[0].get('src')
    duration = TimeToSeconds(':'.join(v.xpath('./div[@class="duration_views"]/h2/text()'))) * 1000
    try:
      rating = float( len( v.xpath('./div[@class="rating"]//img[contains(@src,"starfull")]') ) )
      if len( v.xpath('./div[@class="rating"]//img[contains(@src,"starhalf")]') ) == 1:
        rating += 0.5
    except:
      rating = None
    video_page = v.xpath('./a')[0].get('href')

    dir.Append(Function(WebVideoItem(PlayVideo, title=video_title, duration=duration, rating=rating*2, thumb=Function(GetThumb, url=thumb)), url=video_page))

  if len(video.xpath('.//div[@id="pages"]//a[contains(text(),"Next")]')) > 0:
    dir.Append(Function(DirectoryItem(VideoList, title='Next page...', thumb=R(ICON_MORE)), url=url, sort_url=sort_url, title=title, page=page+1))

  return dir

####################################################################################################

def PlayVideo(sender, url):
  page = HTTP.Request(BASE_URL + url)
  xml_url = re.search('(http://.+?xml=1)', page).group(1)
  location = XML.ElementFromURL(xml_url, errors='ignore', cacheTime=1).xpath('//a:location', namespaces=XML_NS)[0].text
  video_url = PLAYER_URL % ( String.Quote(location, usePlus=True), String.Quote(PQS, usePlus=True) )
  return Redirect(WebVideoItem(video_url))

####################################################################################################

def GetThumb(url):
  data = HTTP.Request(url, cacheTime=CACHE_INTERVAL_LONG)
  if data:
    return DataObject(data, 'image/jpeg')
  return Redirect(R(ICON_DEFAULT))

####################################################################################################

def TimeToSeconds(timecode):
  seconds  = 0
  duration = timecode.split(':')
  duration.reverse()

  for i in range(0, len(duration)):
    seconds += int(duration[i]) * (60**i)

  return seconds
  
####################################################################################################

def GetSort():
  sort = Prefs.Get('video_sort_order')
  for name, url in VIDEO_SORT_ORDER:
    if sort == name:
      return [name, url]
  return ['','']
