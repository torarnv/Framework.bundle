#
#  Plex Extension Framework
#  Copyright (C) 2008-2010 Plex Development Team (James Clarke, Elan Feingold). All Rights Reserved.
#

import os, time, mimetypes, hashlib, urllib, base64, cerealizer, types

def makedirs(path):
  if not os.path.exists(path):
    os.makedirs(path)
    
def timestamp_from_datetime(dt):
  return time.mktime(dt.timetuple())
  
def guess_mime_type(filename):
  mtype = mimetypes.guess_type(filename)[0]
  if mtype: return mtype
  else: return 'application/octet-stream'
  
def urlencode(string):
  encoded = urllib.urlencode({'v':string})
  return encoded[2:]
  
def safe_encode(string):
  return base64.b64encode(string).replace('/','@').replace('+','*').replace('=','_')

def safe_decode(string):
  return base64.b64decode(string.replace('@','/').replace('*','+').replace('_','='))

def pack(obj):
  serialized_obj = cerealizer.dumps(obj)
  encoded_string = safe_encode(serialized_obj)
  return urllib.quote(encoded_string)
  
def unpack(string):
  unquoted_string = urllib.unquote(string)
  decoded_string = safe_decode(unquoted_string)
  return cerealizer.loads(decoded_string)
  
# Checks whether a function accepts a named argument
def function_accepts_arg(f, argname):
  if isinstance(f, types.MethodType):
    f = f.im_func
  if isinstance(f, types.FunctionType):
    return argname in f.func_code.co_varnames[:f.func_code.co_argcount]
  return False

class AttrProxy(object):
  
  # Provies a proxy object that (when inserted into a kit object)
  # allows direct getting & setting of a single component attribute
  # while maintaining sandbox security.
  
  def __init__(self, obj, attr):
    self._obj = obj
    self._attr = attr
    

# using module re to pluralize most common english words
# (rule_tuple used as function default, so establish it first)

import re, string

# (pattern, search, replace) regex english plural rules tuple
rule_tuple = (
('[ml]ouse$', '([ml])ouse$', '\\1ice'), 
('child$', 'child$', 'children'), 
('booth$', 'booth$', 'booths'), 
('foot$', 'foot$', 'feet'), 
('ooth$', 'ooth$', 'eeth'), 
('l[eo]af$', 'l([eo])af$', 'l\\1aves'), 
('sis$', 'sis$', 'ses'), 
('man$', 'man$', 'men'), 
('ife$', 'ife$', 'ives'), 
('eau$', 'eau$', 'eaux'), 
('lf$', 'lf$', 'lves'), 
('[sxz]$', '$', 'es'), 
('[^aeioudgkprt]h$', '$', 'es'), 
('(qu|[^aeiou])y$', 'y$', 'ies'), 
('$', '$', 's')
)

def regex_rules(rules=rule_tuple):
    for line in rules:
        pattern, search, replace = line
        yield lambda word: re.search(pattern, word) and re.sub(search, replace, word)

def plural(noun):
    for rule in regex_rules():
        result = rule(noun)
        if result: 
            return result
            
def function_name(f):
  return f.__name__
            
            
def clean_up_string(s):
  s = unicode(s)

  # Ands.
  s = s.replace('&', 'and')

  # Pre-process the string a bit to remove punctuation.
  s = re.sub('[' + string.punctuation + ']', '', s)
  
  # Lowercase it.
  s = s.lower()
  
  # Strip leading "the/a"
  s = re.sub('^(the|a) ', '', s)
  
  # Spaces.
  s = re.sub('[ ]+', ' ', s).strip()
    
  return s

# From http://en.wikibooks.org/wiki/Algorithm_Implementation/Strings/Longest_common_substring#Python
def longest_common_substring(first, second):
  S = clean_up_string(first)
  T = clean_up_string(second)
  
  m = len(S); n = len(T)
  L = [[0] * (n+1) for i in xrange(m+1)]
  LCS = set()
  longest = 0
  for i in xrange(m):
    for j in xrange(n):
      if S[i] == T[j]:
        v = L[i][j] + 1
        L[i+1][j+1] = v
        if v > longest:
          longest = v
          LCS = set()
        if v == longest:
          LCS.add(S[i-v+1:i+1])
  if len(LCS) > 0:
    return LCS.pop()
  return ''
            
# TODO: Attribution http://www.korokithakis.net/node/87
def levenshtein_distance(first, second):
  first = clean_up_string(first)
  second = clean_up_string(second)
  
  if len(first) > len(second):
    first, second = second, first
  if len(second) == 0:
    return len(first)
  first_length = len(first) + 1
  second_length = len(second) + 1
  distance_matrix = [[0] * second_length for x in range(first_length)]
  for i in range(first_length):
    distance_matrix[i][0] = i
  for j in range(second_length):
    distance_matrix[0][j]=j
  for i in xrange(1, first_length):
    for j in range(1, second_length):
      deletion = distance_matrix[i-1][j] + 1
      insertion = distance_matrix[i][j-1] + 1
      substitution = distance_matrix[i-1][j-1]
      if first[i-1] != second[j-1]:
        substitution = substitution + 1
      distance_matrix[i][j] = min(insertion, deletion, substitution)
  return distance_matrix[first_length-1][second_length-1]