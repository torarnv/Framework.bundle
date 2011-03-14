#
#  Plex Extension Framework
#  Copyright (C) 2008-2010 Plex Development Team (James Clarke, Elan Feingold). All Rights Reserved.
#

import Framework
import os, cerealizer

ISO639_3 = dict(
  aar = 'aa', abk = 'ab', afr = 'af', aka = 'ak', alb = 'sq', amh = 'am', ara = 'ar', arg = 'an',
  arm = 'hy', asm = 'as', ava = 'av', ave = 'ae', aym = 'ay', aze = 'az', bak = 'ba', bam = 'bm',
  baq = 'eu', bel = 'be', ben = 'bn', bih = 'bh', bis = 'bi', bos = 'bs', bre = 'br', bul = 'bh',
  bur = 'my', cat = 'ca', cha = 'ch', che = 'ce', chi = 'zh', chu = 'cu', chv = 'cv', cor = 'kw', 
  cos = 'co', cre = 'cr', cze = 'cs', dan = 'dn', div = 'dv', dut = 'nl', dzo = 'dz', eng = 'en',
  epo = 'eo', est = 'et', ewe = 'ew', fao = 'fo', fij = 'fj', fin = 'fi', fre = 'fr', fry = 'fy', 
  ful = 'ff', geo = 'ka', ger = 'de', gla = 'gd', gle = 'ge', glg = 'gl', ell = 'el', grn = 'gn',
  guj = 'gu', hat = 'ht', hau = 'ha', heb = 'he', her = 'hz', hin = 'hi', hmo = 'ho', hrv = 'hr',
  hun = 'hu', ibo = 'ig', ice = 'is', ido = 'io', iii = 'ii', iku = 'iu', ile = 'ie', ina = 'ia',
  ind = 'id', ipk = 'ik', ita = 'it', jav = 'jv', jpn = 'ja', kal = 'kl', kan = 'kn', kas = 'ks',
  kau = 'kr', kaz = 'kk', khm = 'km', kik = 'ki', kin = 'rw', kir = 'ky', kom = 'kv', kon = 'kg',
  kor = 'ko', kua = 'kj', kur = 'ku', lao = 'lo', lat = 'la', lav = 'lv', lim = 'li', lin = 'ln', 
  lit = 'lt', ltz = 'lb', lub = 'lu', lug = 'lg', mac = 'mk', mah = 'mh', mal = 'ml', mao = 'mi',
  mar = 'mr', may = 'ms', mlg = 'mg', mlt = 'mt', mol = 'mo', mon = 'mn', nau = 'na', nav = 'nv',
  nbl = 'nr', nde = 'nd', ndo = 'ng', nep = 'ne', nno = 'nn', nob = 'nb', nor = 'no', nya = 'ny',
  oci = 'oc', oji = 'oj', ori = 'or', orm = 'om', oss = 'os', pan = 'pa', per = 'fa', pli = 'pi',
  pol = 'pl', por = 'pt', pus = 'ps', que = 'qu', roh = 'rm', run = 'rn', rus = 'ru', sag = 'sg',
  san = 'sa', scc = 'sr', sin = 'si', slo = 'sk', slv = 'sl', sme = 'se', smo = 'sm', sna = 'sn',
  snd = 'sd', som = 'so', sot = 'st', spa = 'es', srd = 'sc', ssw = 'ss', sun = 'su', swa = 'sw',
  swe = 'sv', tah = 'ty', tam = 'ta', tat = 'tt', tel = 'te', tgk = 'tg', tgl = 'tl', tha = 'th',
  tib = 'bo', tir = 'ti', ton = 'to', tsn = 'tn', tso = 'ts', tuk = 'tk', tur = 'tr', twi = 'tw',
  uig = 'ug', ukr = 'uk', urd = 'ur', uzb = 'uz', ven = 've', vie = 'vi', vol = 'vo', wel = 'cy',
  wln = 'wa', wol = 'wo', xho = 'xh', yid = 'yi', yor = 'yo', zha = 'za', zul = 'zu', rum = 'ro',
  pob = 'pb', unk = 'xx', ass = 'ay', un = 'xx'
)

class Language(object):
  Unknown = 'xx'
  Afar = 'aa'
  Abkhazian = 'ab'
  Afrikaans = 'af'
  Akan = 'ak'
  Albanian = 'sq'
  Amharic = 'am'
  Arabic = 'ar'
  Aragonese = 'an'
  Armenian = 'hy'
  Assamese = 'as'
  Avaric = 'av'
  Avestan = 'ae'
  Aymara = 'ay'
  Azerbaijani = 'az'
  Bashkir = 'ba'
  Bambara = 'bm'
  Basque = 'eu'
  Belarusian = 'be'
  Bengali = 'bn'
  Bihari = 'bh'
  Bislama = 'bi'
  Bosnian = 'bs'
  Breton = 'br'
  Bulgarian = 'bg'
  Burmese = 'my'
  Catalan = 'ca'
  Chamorro = 'ch'
  Chechen = 'ce'
  Chinese = 'zh'
  ChurchSlavic = 'cu'
  Chuvash = 'cv'
  Cornish = 'kw'
  Corsican = 'co'
  Cree = 'cr'
  Czech = 'cs'
  Danish = 'da'
  Divehi = 'dv'
  Dutch = 'nl'
  Dzongkha = 'dz'
  English = 'en'
  Esperanto = 'eo'
  Estonian = 'et'
  Ewe = 'ee'
  Faroese = 'fo'
  Fijian = 'fj'
  Finnish = 'fi'
  French = 'fr'
  Frisian = 'fy'
  Fulah = 'ff'
  Georgian = 'ka'
  German = 'de'
  Gaelic = 'gd'
  Irish = 'ga'
  Galician = 'gl'
  Manx = 'gv'
  Greek = 'el'
  Guarani = 'gn'
  Gujarati = 'gu'
  Haitian = 'ht'
  Hausa = 'ha'
  Hebrew = 'he'
  Herero = 'hz'
  Hindi = 'hi'
  HiriMotu = 'ho'
  Croatian = 'hr'
  Hungarian = 'hu'
  Igbo = 'ig'
  Icelandic = 'is'
  Ido = 'io'
  SichuanYi = 'ii'
  Inuktitut = 'iu'
  Interlingue = 'ie'
  Interlingua = 'ia'
  Indonesian = 'id'
  Inupiaq = 'ik'
  Italian = 'it'
  Javanese = 'jv'
  Japanese = 'ja'
  Kalaallisut = 'kl'
  Kannada = 'kn'
  Kashmiri = 'ks'
  Kanuri = 'kr'
  Kazakh = 'kk'
  Khmer = 'km'
  Kikuyu = 'ki'
  Kinyarwanda = 'rw'
  Kirghiz = 'ky'
  Komi = 'kv'
  Kongo = 'kg'
  Korean = 'ko'
  Kuanyama = 'kj'
  Kurdish = 'ku'
  Lao = 'lo'
  Latin = 'la'
  Latvian = 'lv'
  Limburgan = 'li'
  Lingala = 'ln'
  Lithuanian = 'lt'
  Luxembourgish = 'lb'
  LubaKatanga = 'lu'
  Ganda = 'lg'
  Macedonian = 'mk'
  Marshallese = 'mh'
  Malayalam = 'ml'
  Maori = 'mi'
  Marathi = 'mr'
  Malay = 'ms'
  Malagasy = 'mg'
  Maltese = 'mt'
  Moldavian = 'mo'
  Mongolian = 'mn'
  Nauru = 'na'
  Navajo = 'nv'
  SouthNdebele = 'nr'
  NorthNdebele = 'nd'
  Ndonga = 'ng'
  Nepali = 'ne'
  NorwegianNynorsk = 'nn'
  NorwegianBokmal = 'nb'
  Norwegian = 'no'
  Chichewa = 'ny'
  Occitan = 'oc'
  Ojibwa = 'oj'
  Oriya = 'or'
  Oromo = 'om'
  Ossetian = 'os'
  Panjabi = 'pa'
  Persian = 'fa'
  Pali = 'pi'
  Polish = 'pl'
  Portuguese = 'pt'
  Pushto = 'ps'
  Quechua = 'qu'
  RaetoRomance = 'rm'
  Romanian = 'ro'
  Rundi = 'rn'
  Russian = 'ru'
  Sango = 'sg'
  Sanskrit = 'sa'
  Serbian = 'sr'
  Sinhalese = 'si'
  Slovak = 'sk'
  Slovenian = 'sl'
  Sami = 'se'
  Samoan = 'sm'
  Shona = 'sn'
  Sindhi = 'sd'
  Somali = 'so'
  Sotho = 'st'
  Spanish = 'es'
  Sardinian = 'sc'
  Swati = 'ss'
  Sundanese = 'su'
  Swahili = 'sw'
  Swedish = 'sv'
  Tahitian = 'ty'
  Tamil = 'ta'
  Tatar = 'tt'
  Telugu = 'te'
  Tajik = 'tg'
  Tagalog = 'tl'
  Thai = 'th'
  Tibetan = 'bo'
  Tigrinya = 'ti'
  Tonga = 'to'
  Tswana = 'tn'
  Tsonga = 'ts'
  Turkmen = 'tk'
  Turkish = 'tr'
  Twi = 'tw'
  Uighur = 'ug'
  Ukrainian = 'uk'
  Urdu = 'ur'
  Uzbek = 'uz'
  Venda = 've'
  Vietnamese = 'vi'
  Volapuk = 'vo'
  Welsh = 'cy'
  Walloon = 'wa'
  Wolof = 'wo'
  Xhosa = 'xh'
  Yiddish = 'yi'
  Yoruba = 'yo'
  Zhuang = 'za'
  Zulu = 'zu'
  Brazilian = 'pb'
  NoLanguage = 'xn'
  
  @classmethod
  def All(cls):
    # Iterate through all class attributes, create a list of any strings found, and return it
    all_languages = []
    for name in dir(cls):
      if name[0] != '_':
        attr = getattr(cls, name)
        if isinstance(attr, basestring) and attr != 'xx':
          all_languages.append(attr)
    return all_languages
  
  @classmethod
  def Match(cls, name):
    """
      Attempt to match a given string to a language. Returns the unknown code (xx) if no match
      could be found.
    """
    # Check for a matching 3-char language code
    if name.lower() in ISO639_3:
      return ISO639_3[name.lower()]
    
    # Check for a named language or 2-char language code
    for key in cls.__dict__:
      if key[0] != '_' and (key.lower() == name.lower() or getattr(cls, key) == name.lower()):      
        return getattr(cls, key)
    
    # If nothing was found, return the Unknown code
    return cls.Unknown


# Subclass of str - dynamically localizes when converted to str
class LocalString(object):
  def __init__(self, core, key, locale=None):
    self._core = core
    self._locale = locale
    if isinstance(key, LocalString):
        self._key = key._key
    else:
        self._key = key
    str.__init__(self)
    
  # Conversion to regular string or unicode
  def __str__(self):
    return self._core.localization.localize(self._key, self._locale)
  def __unicode__(self):
    return unicode(self.__str__())
        
  # Representation  
  def __repr__(self):
    return "Framework.components.localization.LocalString(" + repr(self._key) + ")"

  # Support for the + operator while retaining dynamic localization
  def __add__(self,other):
    return LocalStringPair(self, other, self._locale)
    
  def __radd__(self,other):
    return LocalStringPair(other, self, self._locale)
    
  def localize(self, locale):
    return self._core.localization.localize(self._key, locale)
  
  
class LocalStringPair(object):

  # Store both objects
  def __init__(self, string1, string2, locale=None):
    self._string1 = string1
    self._string2 = string2
    self._locale = locale

  # Conversion to regular string or unicode
  def __str__(self):
    return self._string1.__str__() + self._string2.__str__()
  def __unicode__(self):
    return unicode(self.__str__())

  # Representation
  def __repr__(self):
    return "Framework.components.localization.LocalStringPair(" + repr(self._string1) + ", " + repr(self._string2) + ")"

  def __add__(self, other):
    return LocalStringPair(self, other, self._locale)
    
  def __radd__(self, other):
    return LocalStringPair(other, self, self._locale)
    
  def localize(self, locale):
    s1 = self._string1
    s2 = self._string2
    if isinstance(s1, (LocalString, LocalStringPair)):
      s1 = s1.localize(locale)
    if isinstance(s2, (LocalString, LocalStringPair)):
      s2 = s2.localize(locale)
    return s1 + s2
    
    
# Similar to LocalStringPair, but uses the second object for string formatting
class LocalStringFormatter(LocalStringPair):
  def __str__(self):
    return self._string1.__str__() % self._string2
  def __repr__(self):
    return "Framework.components.localization.LocalStringFormatter(" + repr(self._string1) + ", " + repr(self._string2) + ")"    

  def localize(self, locale):
    s1 = self._string1
    s2 = self._string2
    if isinstance(s1, (LocalString, LocalStringPair)):
      s1 = s1.localize(locale)
    return s1 % s2

class Localization(Framework.bases.BaseComponent):
  
  def _init(self):
    self._current_locale = None
    self._default_locale = None
    
    self._lang_dicts = {}
    self._country_dicts = {}
    self._default_lang_dict = {}
    self._default_country_dict = {}
    
    self.language = Language
    
    self.default_locale = self._core.config.default_locale
    
  def language_code_valid(self, lang):
    for name in self.language.__dict__:
      if name[0] == '_': continue
      value = getattr(self.language, name)
      if value == lang:
        return True
    return False
    
  def local_string(self, key, locale=None):
    return LocalString(self._core, key, locale)
    
  def local_string_with_format(self, key, locale=None, *args):
    return LocalStringFormatter(LocalString(self._core, key, locale), tuple(args))
    
  def localize(self, key, locale=None):
    # If no locale is provided, use the default
    if locale == None:
      locale = self.default_locale
    else:
      self.load_locale(locale)
        
    # Check for a country-specific string first, then a language-specific one.
    def do_localize(locale):
      pos = locale.find('-')
      if pos > -1:
        lang = locale[:pos]
      else:
        lang = locale
        locale = None
      if locale in self._country_dicts and key in self._country_dicts[locale]:
        return self._country_dicts[locale][key]
      elif lang in self._lang_dicts and key in self._lang_dicts[lang]:
        return self._lang_dicts[lang][key]
      return None
      
    # Try to find a value using the provided locale
    value = do_localize(locale)
    if value: return value
    
    # If no value was found, try the default locale instead
    value = do_localize(self.default_locale)
    if value: return value
    
    # If we still couldn't localise, return the key
    return key
    
  @property
  def default_locale(self):
    return self._default_locale
    
  @default_locale.setter
  def default_locale(self, loc):
    if loc == self._default_locale: return
    self._core.log.info("Setting the default locale to "+loc)
    self._default_locale = loc
    self.load_locale(loc)
      
  def load_locale(self, loc):
    
    # Check whether we're being given a language only ('en') or a language and location ('en-us')
    pos = loc.find('-')
    
    # Language + Location - try to load both dicts
    if pos > -1:
      lang = loc[:pos]
      langPath = os.path.join(self._core.bundle_path, 'Contents', 'Strings', lang + '.json')
      if lang not in self._lang_dicts:
        if os.path.exists(langPath):
          try:
            json = self._core.storage.load(langPath)
            self._lang_dicts[lang] = self._core.data.json.from_string(json)
            self._core.log.debug("Loaded %s strings" % lang)
          except:
            self._core.log.error("Exception when trying to load %s strings" % lang)
        else:
          self._core.log.debug("Unable to find %s strings" % lang)
      
      locPath = os.path.join(self._core.bundle_path, 'Contents', 'Strings', loc + '.json')
      if loc not in self._country_dicts:
        if os.path.exists(locPath):
          try:
            json = self._core.storage.load(locPath)
            self._country_dicts[loc] = self._core.data.json.from_string(json)
            self._core.log.debug("Loaded %s strings" % loc)
          except:
            self._core.log.error("Exception when trying to load %s strings" % loc)
        else:
          self._core.log.debug("Unable to find %s strings" % loc)
    
    # Language only
    else:
      langPath = os.path.join(self._core.bundle_path, 'Contents', 'Strings', loc + '.json')
      if loc not in self._lang_dicts:
        if os.path.exists(langPath):
          try:
            json = self._core.storage.load(langPath)
            self._lang_dicts[loc] = self._core.data.json.from_string(json)
            self._core.log.debug("Loaded %s strings" % loc)
          except:
            self._core.log.error("Exception when trying to load %s strings" % loc)
        else:
          self._core.log.debug("Unable to find %s strings" % loc)
        