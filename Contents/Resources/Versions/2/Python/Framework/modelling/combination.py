#
#  Plex Extension Framework
#  Copyright (C) 2008-2010 Plex Development Team (James Clarke, Elan Feingold). All Rights Reserved.
#

import Framework
import os, os.path, sys
import templates
from copy import deepcopy

excluded_attr_names = ['save_externally']

if sys.platform == 'win32':
  import ctypes
  kdll = ctypes.windll.LoadLibrary("kernel32.dll")

class Combinable(object): pass

class BundleCombiner(object):
  
  def __init__(self, core, model_path, config_path):
    self._core = core
    self._model_path = model_path
    self._config_path = config_path

  def _symlink(self, src, dst):
    
    # Remove old link if it exists.
    if os.path.exists(dst):
      try: os.unlink(dst)
      except: pass
    
    try:
      # Platform dependent way of creating a new link.
      if sys.platform == 'win32':
        is_dir = 1 if os.path.isdir(src) else 0
        
        # Turn the source into an absolute path and create a hard link.
        full_src = os.path.normpath(os.path.join(os.path.dirname(dst), src))
        res = kdll.CreateHardLinkW(unicode(longpathify(dst)), unicode(longpathify(full_src)), 0)
        if res == 0:
          self._core.log.debug("Error creating hard link from [%s] to [%s]", src, dst)
      else:
        os.symlink(src, dst)
        
    except:
      pass

  def _combine_attr(self, root_path, internal_path, attr, config_identifier, config_el, candidates, p_sources, template):
    
    out_path = os.path.join(root_path, '_combined', internal_path)
    
    # Apply source rules from the config
    p_sources = self._apply_sources(p_sources, config_identifier, config_el)
    name = template.__name__
    
    # Remove any sources that don't have an attribute candidate
    for source in p_sources:
      if source not in candidates:
        p_sources.remove(source)
    
    # Get the attribute rules
    rules = self._get_rules(config_el)
    
    # Get the rule action
    rule_action = config_el.get('action')
    
    # If no action is defined, set a default based on the template class
    if rule_action == None:
      if isinstance(attr, templates.MapTemplate):
        rule_action = 'merge'
      else:
        rule_action = 'override'
    
    # Combine values
    if isinstance(attr, templates.ValueTemplate):
      #TODO: Account for external values
      if rule_action == 'override':
        for source in p_sources:
          if source in candidates and candidates[source].text is not None:
            return candidates[source]
      else:
        raise Framework.FrameworkException("Unable to perform the action '%s' on an object of type %s" % (rule_action, type(attr)))
      
    
    # Combine records  
    elif isinstance(attr, templates.RecordTemplate):
      # TODO: Record combination
      print "TODO: Record combination"
      
      
    # Combine proxy containers
    elif isinstance(attr, templates.ProxyContainerTemplate):
      attr_el = self._core.data.xml.element(name)
      
      symlink_map = {}
      for source in p_sources:
        if source in candidates:
          source_dir_path = os.path.join(root_path, source, internal_path)
          if os.path.exists(source_dir_path):
            Framework.utils.makedirs(out_path)
            for item_el in candidates[source].xpath('item'):
              proxy_type = None
              
              # Find the proxy type
              for key in item_el.keys():
                if key not in ['external', 'url']:
                  proxy_type = key
                  filename = item_el.get(key)
                  break
              if not proxy_type:
                raise Framework.FrameworkException('Proxy item %s has no type.', item_el)
              
              # Calculate the relative path for the symlink
              source_file_path = os.path.join(source_dir_path, filename)
              combined_filename = source + '_' + filename
              link_path = os.path.join(out_path, combined_filename)
              rel_path = os.path.relpath(source_file_path, out_path)
              
              # Copy the item element
              item_copy = deepcopy(item_el)
              
              # Check whether a stored file exists
              stored_file_path = link_path.replace('_combined', '_stored')
              if os.path.exists(stored_file_path):
                # The stored file exists - modify the path & XML accordingly
                rel_path = os.path.relpath(stored_file_path, out_path)
                if proxy_type == 'preview':
                  del item_copy.attrib['preview']
                proxy_type = 'media'
              
              symlink_map[rel_path] = link_path
              
              item_copy.set(proxy_type, combined_filename)
              attr_el.append(item_copy)

        # If we are overriding, not merging, break when the symlink map becomes populated after checking a source
        if rule_action == 'override' and len(symlink_map) > 0:
          break

      # Make the symlinks.
      for source in symlink_map:
        self._symlink(source, symlink_map[source])

      return attr_el
      
      
    # Combine directories
    elif isinstance(attr, templates.DirectoryTemplate):
      symlink_map = {}
      for source in p_sources:
        source_dir_path = os.path.join(root_path, source, internal_path)
        if os.path.exists(source_dir_path):
          Framework.utils.makedirs(out_path)
          for filename in os.listdir(source_dir_path):
            # Calculate the relative path for the symlink
            source_file_path = os.path.join(source_dir_path, filename)
            link_path = os.path.join(out_path, source + '_' + filename)
            rel_path = os.path.relpath(source_file_path, out_path)
            symlink_map[rel_path] = link_path
        
        # If we are overriding, not merging, break when the symlink map becomes populated after checking a source
        if rule_action == 'override' and len(symlink_map) > 0:
          break
          
      # Make the symlinks.
      for source in symlink_map:
        self._symlink(source, symlink_map[source])
      
      return self._core.data.xml.element(name)
        
    
    # Combine maps
    elif isinstance(attr, templates.MapTemplate):
      # If overriding, use the items from the first populated source
      if rule_action == 'override':
        item_map = {}
        for source in p_sources:
          if source in candidates:
            for item_el in candidates[source].xpath('item'):
              item_map[item_el.get('key')] = item_el
            break
        
        # Create a combined element
        attr_el = self._core.data.xml.element(name)
        for item_name in item_map:
          attr_el.append(item_map[item_name])
        
        # Return it
        return attr_el
      
      # TODO: Merge child attributes          
      
      elif rule_action == 'merge':
        
        # Get candidates for each item
        item_candidate_sets = {}
        for source in p_sources:
          if source in candidates:
            for item_el in candidates[source].xpath('item'):
              key = item_el.get('key')
              if key not in item_candidate_sets:
                item_candidate_sets[key] = {}
            
              # If the item is saved externally, discard the current element and load the contents of the XML file
              if bool(item_el.get('external')) == True:
                item_xml_path = os.path.join(root_path, source, internal_path, key+'.xml')
                item_xml_str = self._core.storage.load(item_xml_path)
                item_el = self._core.data.xml.from_string(item_xml_str)
              
              item_candidate_sets[key][source] = deepcopy(item_el)
          
        # Get a config element for the current item
        # TODO: Fix?
        if name in rules:
          rule = rules[name]
        else:
          rule = self._core.data.xml.element('attribute')
        
        # Create a new element for the map attribute
        attr_el = self._core.data.xml.element(name)
        
        # Get the item template and class name
        item_template = template._item_template
        class_name = type(item_template).__name__
        setattr(item_template, '__name__', 'item')
        
        for key in item_candidate_sets:
          item_candidates = item_candidate_sets[key]
          
          # Combine the item
          if isinstance(item_template, templates.RecordTemplate):
            item_el = self._combine_object(root_path, os.path.join(internal_path, key), config_identifier, rule, item_candidates, list(p_sources), item_template)
          else:
            item_el = self._combine_attr(root_path, os.path.join(internal_path, key), attr._item_template, config_identifier, rule, item_candidates, list(p_sources), item_template)
        
          # If combined successfully, process the item
          if item_el is not None:
            # If the map is stored internally, append the element
            if not attr._item_template._external:
              item_el.set('key', key)
              attr_el.append(item_el)
              
            # If stored externally, write the element to a file and append a stub
            else:
              item_out_path = os.path.join(out_path, key)
              Framework.utils.makedirs(out_path)
              item_el.tag = class_name
              item_xml_str = self._core.data.xml.to_string(item_el)
              self._core.storage.save(item_out_path + '.xml', item_xml_str)
              ext_el = self._core.data.xml.element('item')
              ext_el.set('external', str(True))
              ext_el.set('key', key)
              attr_el.append(ext_el)
        
        # Return the combined map element   
        return attr_el
          
        
          
      
    elif isinstance(attr, templates.SetTemplate):
      item_list = []
      
      for source in p_sources:
        if source in candidates:
          attr_el = candidates[source]
          for item_el in attr_el.xpath('item'):
            item_list.append(item_el)
          
        # If we are overriding, not merging, break when the item list becomes populated after checking a source
        if rule_action == 'override' and len(item_list) > 0:
          break
          
      # Update the index values and create a combined element
      attr_el = self._core.data.xml.element(name)
      count = 0
      for item_el in item_list:
        item_el.set('index', str(count))
        count += 1
        attr_el.append(item_el)
      
      return attr_el
      #el.append(attr_el)
          
    elif isinstance(attr, templates.LinkTemplate):
      if rule_action == 'override':
        for source in p_sources:
          if source in candidates and candidates[source].text is not None:
            return candidates[source]
      else:
        raise Framework.FrameworkException("Unable to perform the action '%s' on an object of type %s" % (rule_action, type(attr)))
      
    else:
      raise Framework.FrameworkException("Unable to combine object of type "+str(type(attr)))
    
  def _apply_sources(self, p_sources, config_identifier, config_el):
    sources_config = config_el.xpath('sources')
    if len(sources_config) > 0:
      sc_el = sources_config[0]
      action = sc_el.get('action')
      if action == None or action == 'override':
        p_sources = list()
      elif action == 'append':
        pass
      else:
        raise Framework.FrameworkException("Unknown action '%s'" % action)
      for agent_el in sc_el.xpath('agent'):
        p_sources.append(agent_el.text)
    if config_identifier not in p_sources:
      p_sources.append(config_identifier)
    return p_sources
    
  def _get_rules(self, config_el):
    rules = {}
    for attr_el in config_el.xpath('rules/attribute'):
      attr_name = attr_el.get('name')
      rules[attr_name] = attr_el
    return rules
        
  def _combine_object(self, root_path, internal_path, config_identifier, config_el, candidates, p_sources, template):
    out_path = os.path.join(root_path, '_combined', internal_path)
    
    # Apply any source changes specified in the config file
    p_sources = self._apply_sources(p_sources, config_identifier, config_el)

    # Check for rules to apply to attributes
    rules = self._get_rules(config_el)
    
    # Create a new element for the combined object
    el = self._core.data.xml.element(template.__name__)
    
    if isinstance(template, templates.RecordTemplate):
      attrs = dir(type(template))
    else:
      attrs = dir(template)
    
    for name in attrs:
      if name in excluded_attr_names or name[0] == '_':
        continue
      attr = getattr(template, name)
      if isinstance(attr, templates.AttributeTemplate):
        if name in rules:
          rule = rules[name]
        else:
          rule = self._core.data.xml.element('attribute')
        
        # Get the available candidates for the attribute
        attr_candidates = {}
        for source in candidates:
          source_el_list = candidates[source].xpath(name)
          if len(source_el_list) > 0:
            attr_candidates[source] = deepcopy(source_el_list[0])
        
        attr_template = getattr(template, name)
        setattr(attr_template, '__name__', name)
        attr_el = self._combine_attr(root_path, os.path.join(internal_path, name), attr, config_identifier, rule, attr_candidates, list(p_sources), attr_template)
        if attr_el != None:
          el.append(attr_el)
        
    return el
    
  def _combine_file(self, root_path, internal_path, config_identifier, config_el, a_sources, p_sources, template):
    candidates = {}
    for a_source in a_sources:
      file_path = os.path.join(root_path, a_source, internal_path, 'Info.xml')
      if os.path.exists(file_path):
        source_xml_str = self._core.storage.load(file_path)
        source_el = self._core.data.xml.from_string(source_xml_str)
        candidates[a_source] = source_el
        
    return self._combine_object(root_path, internal_path, config_identifier, config_el, candidates, list(p_sources), template)
    
    
  def contributing_agents(self, cls, config_identifier, include_config_identifier=False):
    class_name = Framework.utils.plural(cls.__name__.replace('_', ' '))
    config_file_path = os.path.join(self._config_path, config_identifier, class_name + '.xml')
    if not self._core.storage.file_exists(config_file_path):
      return []
      
    config_str = self._core.storage.load(config_file_path)
    config_el = self._core.data.xml.from_string(config_str)
    agents = []
    for agent_el in config_el.xpath('//agent'):
      if agent_el.text not in agents and (include_config_identifier or agent_el.text != config_identifier):
        agents.append(agent_el.text)
    return agents
    

  def combine(self, cls, config_identifier, guid):
    class_name = Framework.utils.plural(cls.__name__.replace('_', ' '))
    guid_hash = self._core.data.hashing.sha1(guid)
    bundle_path = os.path.join(self._model_path, class_name, guid_hash[0], guid_hash[1:] + '.bundle')
    config_file_path = os.path.join(self._config_path, config_identifier, class_name + '.xml')
    template = cls._template
    
    if self._core.storage.file_exists(config_file_path):
      config_str = self._core.storage.load(config_file_path)
      config_el = self._core.data.xml.from_string(config_str)
    else:
      config_el = self._core.data.xml.element('combine')
      
    available_sources = [config_identifier]
    preferred_sources = ['_custom']
    
    # Get a list of available data sources
    root_path = os.path.join(bundle_path, 'Contents')
    for name in os.listdir(root_path):
      if name[0] != '_' or name == '_custom':
        available_sources.append(name)

    # Whack the existing combined directory
    out_path = self._core.storage.join_path(root_path, '_combined')
    self._core.storage.remove_tree(out_path)
    out_file_path = self._core.storage.join_path(out_path, 'Info.xml')
    
    el = self._combine_file(root_path, '', config_identifier, config_el, available_sources, preferred_sources, template)
    
    xml_str = self._core.data.xml.to_string(el)
    Framework.utils.makedirs(out_path)
    self._core.storage.save(out_file_path, xml_str)
    