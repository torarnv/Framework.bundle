#
#  Plex Extension Framework
#  Copyright (C) 2008-2010 Plex Development Team (James Clarke, Elan Feingold). All Rights Reserved.
#

import Framework

class ProxyTemplateKit(object):
  Preview         = Framework.modelling.templates.ProxyTemplate('Preview')
  Media           = Framework.modelling.templates.ProxyTemplate('Media')
  

class TemplateKit(Framework.bases.BaseKit):
  """
    TemplateKit is a very simple API that provides access to the template classes
    in Framework.modelling for use when defining model templates.
  """

  Abstract        = Framework.modelling.templates.AbstractTemplate
  Model           = Framework.modelling.templates.ModelTemplate
  Record          = Framework.modelling.templates.RecordTemplate
  Link            = Framework.modelling.templates.LinkTemplate
  
  Set             = Framework.modelling.templates.SetTemplate
  Map             = Framework.modelling.templates.MapTemplate
  Directory       = Framework.modelling.templates.DirectoryTemplate
  ProxyContainer  = Framework.modelling.templates.ProxyContainerTemplate
  
  String          = Framework.modelling.templates.StringTemplate
  Integer         = Framework.modelling.templates.IntegerTemplate
  Float           = Framework.modelling.templates.FloatTemplate
  Boolean         = Framework.modelling.templates.BooleanTemplate
  Date            = Framework.modelling.templates.DateTemplate
  Time            = Framework.modelling.templates.TimeTemplate
  Datetime        = Framework.modelling.templates.DatetimeTemplate
  
  Data            = Framework.modelling.templates.DataTemplate
  Proxy           = ProxyTemplateKit