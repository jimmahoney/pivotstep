#!BPY
"""
  dancers.py

A python script to automate dancer animations in blender.

Requires the corresponding blender file dancers.blend.

To see its print output, either 
 (a) launch blender from the command line (optional: give position), e.g.
       $ blender -p 10 10 2160 1500 dancer_14.blender &
     Sync this script with the pivotstep.py text object within blender
     (if it has been edited externally), and run it from within blender,
     for example with alt-p from within its text window
 (b) or run the whole script through blender from the command line, 
     perhaps sending print output to a file.
       $ blender dancer_26.blender -P pivot_step.py > output.txt

From Blender's interactive python, these functions and classes
can be loaded with "from pivotstep import *".

Jim Mahoney, Marlboro College, GPL

"""

import bpy
import Blender
import time
from Blender import Ipo
from Blender import Mathutils
from math import pi


script_name = 'dancers.py'
script_date = '2010-03-22'

start_frame = 1

# action ipos, i.e. motion of bones relative to model center
act_position_keys = [Ipo.PO_LOCX, Ipo.PO_LOCY, Ipo.PO_LOCZ]
act_rotation_keys = [Ipo.PO_QUATW, Ipo.PO_QUATX, Ipo.PO_QUATY, Ipo.PO_QUATZ]
act_position_rotation_keys = sum([act_position_keys, act_rotation_keys], [])


blender_data = {
  'steps' : [
    'default action',         # all bones, special "background" action
    'embrace man',            # arms,      embrace
    'embrace woman',          # arms,      embrace
    'step forward L to R',    # legs,      step
    'step forward R to L',    # legs,      step
    'step back L to R',       # legs,      step
    'step back R to L',       # legs,      step
    'step side L to R',       # legs,      step
    'step side R to L',       # legs,      step
    'step shift L to R',      # legs,      step
    'step shift R to L',      # legs,      step
    ],
  'poses' : [             # the blender pose library is the 'PoseLib' action
    'default pose',
    'arms at sides',
    'feet together',
    'stand on left foot',
    'stand on right foot',
    'embrace man pose',
    'embrace woman pose',
    ],
  }


def get(thing):
  """ Return the named blender object or throw an error if not found.
      If the arg is a name, find the first matching thing with that name
      in the list of blender data types; otherwise, just quietly return thing.
      """
  data_types = [bpy.data.objects, 
                bpy.data.actions, 
                bpy.data.ipos,
                ]
  data_types_string = "bpy.data.(objects,actions,ipos)"
  if type(thing)==type(""):
    for dict in data_types:
      try: 
        return dict[thing]
      except:
        pass
    raise Exception("Nothing named '%s' found in %s." % \
                    (thing, data_types_string))
  else:
    try:
      return thing.action        # a Step or ActionStrip returns its action
    except:
      return thing


def blender_frame(new_frame=None, redraw=False):
  """ Set blender frame if one is given, return current frame,
      and optionally redraw 3D windows. """
  ## print " blender_frame: type(new_frame) = '%s'" % str(type(new_frame))
  if new_frame == None:
    current = Blender.Get('curframe')
  else:
    new_frame = int(new_frame)   # in case a float is passed
    current = new_frame
    Blender.Set('curframe', new_frame)    
  if redraw:
    Blender.Redraw()
  return current

def offset_and_rotation_to_matrix(offset, rotation):  
  """ Return 4x4 transform given offset and (3x3 or quaternion) rotation."""
  if type(rotation).__name__ == 'quaternion':
    rotation = rotation.toMatrix()
  return rotation.resize4x4() * Mathutils.TranslationMatrix(offset)

def max_matrix(matrix):
  """ Return largest absolute value in a python or blender matrix. """
  py_matrix = list(list(x) for x in matrix)
  return max(abs(x) for x in sum(py_matrix, []))


class Step:
  """ Manipulations of the model's actions. """

  symmetric = {'R' : 'L',
               'L' : 'R',
               'forward' : 'back',
               'back' : 'forward',
               'side' : 'side',
               'shift' : 'shift'
               }

  @staticmethod
  def flip(stepname):
    """ Return name of mirrored step, e.g. Step.mirror('L') is 'R'. """
    return Step.symmetric[stepname]

  def __init__(self, which, foot='L', mirror=False):
    """ Create a Step from either
          (a) the full (long) name of an action, 
          (b) an abbreviated (short) name, or 
          (c) an actionstrip.
        The short names may also specify the starting foot and symmetry.
        """
    try:
      self.action = get(which)
    except:
      try:
        self.action = get(self.shortname2longname(which, foot, mirror))
      except:
        raise Exception("No such step '%s'" % which)

  def shortname2longname(self, name, foot, mirror):
    """ Return a long step name (e.g. 'step forward L to R')
        given a short name (e.g. 'forward').  
        """
    try:
      if mirror:
        (name, foot) = (Step.flip(name), Step.flip(foot))
      return 'step ' + name + ' ' + foot + ' to ' + Step.flip(foot)
    except:
      raise Exception('unknown step or foot name')
      
  def is_motion(self):
    """ Return True if this is a motion step, i.e. legs moving body. """
    # as opposed to an arm position or embrace or other non-motion action
    # The current scheme is based on blender names, 
    # setting first part of name to "step" to signal that it is.
    return self.action.name[0:4] == 'step'

  def bone_transform(self, bone_name="Root"):
    """ Return 4x4 transform matrix giving bone's chage. """
    frames = self.action.getFrameNumbers()
    (first, last) = (frames[0], frames[-1])
    ipo = self.action.getChannelIpo(bone_name)
    position_first = Mathutils.Vector( \
      list(ipo[key][first] for key in act_position_keys))
    position_last = Mathutils.Vector( \
      list(ipo[key][last] for key in act_position_keys))
    rotation_first = Mathutils.Quaternion( \
      list(ipo[key][first] for key in act_rotation_keys))
    rotation_last = Mathutils.Quaternion( \
      list(ipo[key][last] for key in act_rotation_keys))
    delta_position = position_last - position_first
    delta_rotation = Mathutils.DifferenceQuats(rotation_last, rotation_first)
    return offset_and_rotation_to_matrix(delta_position, delta_rotation)


class Model:
  """ An animated figure. """

  blender_names = {         # names hardcoded in the dancer_*.blender file.
    'armature' : 'mannequin',
    'models' : ['dancer male', 'dancer female'],
    'model_layers' : [3, 4],
    }

  model_nicknames = {'man': 0, 'woman': 1}    # indeces in model* lists above

  embraces = {'man' : 'embrace man',
              'woman' : 'embrace woman',
              }
  embrace_positions = {
    # change in (location, rotation), for use with blender.object.loc and .rot
    'woman' : ((-0.407804, -1.579339, 0.0), (0.0, 0.0, pi)),
    'man' : ((0.407804, 1.579339, 0.0), (0.0, 0.0, pi)),
    }

  def __init__(self, which='man'):
    if which in self.model_nicknames:
      index = self.model_nicknames[which]
      self.nickname = which
      self.model_layer = self.blender_names['model_layers'][index]
      self.model_name = self.blender_names['models'][index]
      self.model = get(self.model_name)
      self.armature = get(self.blender_names['armature'])
    else:
      raise Exception('no such model')

  def ipo_key(self, which='LOCROT'):
    """ insert an ipo key (default location,rotation) at current frame. """
    self.model.insertIpoKey(Blender.Object.IpoKeyTypes[which])

  def reset(self):
    """ Put model into default state : 
         (1) Delete all but 0th 'default action' actionstrip.
         (2) Set position and rotation to zero.
         (3) Initialize object ipo.
        """
    for strip in self.model.actionStrips:
      if strip.action.name == 'default action':
        strip.stripStart = start_frame
        strip.stripEnd = start_frame
      else:
        self.model.actionStrips.remove(strip)
    self.model.loc = (0.0, 0.0, 0.0)
    self.model.rot = (0.0, 0.0, 0.0)
    self.model.clearIpo()
    blender_frame(start_frame)
    self.ipo_key()

  def embrace(self, partner=None):
    """ Put upper body in the male or female embrace.
        If partner given, move to the appropriate place. """
    # * I expect to have more variations here eventually
    #   (i.e. open and closed and between) along with changes over time.
    # * This is very similar to add_motion(), but different enough
    #   that putting the exceptions there felt messy.
    # * For now I'm only doing (x,y) position and z rotation embrace offsets.
    if not self.nickname in self.embraces:
      raise Exception('Unable to put this model into an embrace.')
    strip = self.add_action(self.embraces[self.nickname])
    strip.stripStart = start_frame   # only while just 1 embrace
    strip.stripEnd = start_frame     # don't change last_frame()
    strip.stripEnd = self.last_frame()      
    if partner:
      (location, rotation) = self.embrace_positions[self.nickname]
      self.model.LocX = partner.model.LocX + location[0]
      self.model.LocY = partner.model.LocY + location[1]
      self.model.RotZ = partner.model.RotZ + rotation[2]
    self.ipo_key()

  def walk_sequence(self, starting_foot, steps, 
                    partner=None, frames_per_step=12):
    """ Assign a series of steps to model and partner. """
    # steps is an array of strings of step names without feet, 
    # e.g. ['forward', 'shift', 'side', 'shift', 'back']
    self.reset()
    self.embrace()
    foot = starting_foot
    for s in steps:
      self.add_motion(Step(s, foot), frames_per_step)
      foot = Step.flip(foot)
    self.housekeeping()
    if partner:
      partner.reset()
      partner.embrace(self)
      foot = Step.flip(starting_foot)
      for s in steps:
        partner.add_motion(Step(Step.flip(s), foot), frames_per_step)
        foot = Step.flip(foot)
      partner.housekeeping()

  def housekeeping(self):
    """ Make adjustements to keep things consistent:
         (a) Set strip 0 'default action' length to last_frame().
         (b) Ditto for last strip if it isn't a motion strip.
         """
    self.model.actionStrips[0].stripEnd = self.last_frame()
    if not Step(self.model.actionStrips[-1]).is_motion():
      self.model.actionStrips[-1].stripEnd = self.last_frame()
    blender_frame(start_frame)

  def summary(self):
    """ Return text string summarizing models."""
    return " models: " + str(self.model_nicknames.keys())

  def fix_transform(self, transform, frame):
    """ Return adjusted transform, compensating for a) mannequin size, 
        b) model size, and c) model orientation at given frame."""
    ## print " fix_transform: transform = '%s'" % str(transform)
    ## print " fix_transform: frame = '%s'" % str(frame)
    model_scale = self.model.size[0]       # assuming same scaling in x,y,z
    armature_scale = self.armature.size[0] # ditto
    offset = transform.translationPart()
    #
    # scaled_offset = offset * model_scale * armature_scale
    ## Hmmm. The scaling seems to be going in twice, so I'll try it this way.
    scaled_offset = offset * armature_scale
    #
    if frame > 0:
      blender_frame(frame)
      model_orientation = self.model.getMatrix().rotationPart()
    else:
      model_orientation = Mathutils.Matrix([1,0,0],[0,1,0],[0,0,1])
    rotated_scaled_offset = scaled_offset * model_orientation
    new_transform = offset_and_rotation_to_matrix(rotated_scaled_offset, 
                                                  transform.rotationPart())
    return new_transform

  def place_actionstrip(self, where, strip):
    """ Move model during actionstrip with given 4x4 matrix transform
        relative to previous actionstrip, by adding keys to model's ipo."""
    # 1. Scale and reposition transform from model's previous location,size.
    ## print " place_actionstrip: where = '%s'" % str(where)
    ## print " ditto  : strip = '%s'" % str(strip)
    ## print " ditto  : strip.stripStart = '%s'" % str(strip.stripStart)
    where = self.fix_transform(where, strip.stripStart - 1)
    # 2. Set frame to start of strip.
    blender_frame(strip.stripStart)
    # 3. Move model position to transform required by previous strip.
    model_matrix = self.model.getMatrix()
    new_matrix = model_matrix * where
    self.model.setMatrix(new_matrix)
    # 4. Insert ipo key : object.insertIpoKey(keytype) for existing locs and rots
    self.ipo_key()
    # 5. Also key next to last frame.
    blender_frame(strip.stripEnd - 1)
    self.ipo_key()

  def add_action(self, action):
    """ Add an action to end of actionstrips, and return the new strip. """
    action = get(action)  # get blender object if given name
    actionStrips = self.model.actionStrips
    actionStrips.append(action) # API docs claim strip is returned
    strip = actionStrips[-1]    # ... but didn't.  This worked.
    strip.groupTarget = self.armature
    return strip

  def add_motion(self, motion, frame_duration='default'):
    """ Add a movement action, and adjust object location accordinly. """
    strip = self.add_action(motion)
    actionStrips = self.model.actionStrips
    if frame_duration == 'default':
      frame_duration = strip.actionEnd - strip.actionStart
    index = len(actionStrips) - 1
    while True:           # move action strip up past any non-step motions
      if index == 1:
        previous_strip = None
        previous_step = None
        break
      previous_strip = actionStrips[index-1]
      previous_step = Step(previous_strip)
      if previous_step.is_motion():
        break
      else:
        actionStrips.moveUp(strip)
        index = index - 1
    if previous_strip:
      strip.stripStart = previous_strip.stripEnd
    else:
      strip.stripStart = start_frame
    strip.stripEnd = strip.stripStart + frame_duration
    if previous_step:
      # Key model ipo location and rotation at start of new strip
      # so that motion continues from end of previous strip.
      previous_motion = previous_step.bone_transform()
    else:
      previous_motion = Mathutils.Matrix().identity().resize4x4()
    self.place_actionstrip(previous_motion, strip)

  def last_frame(self):
    """ Return biggest actionstrip.stripEnd from model's actionstrips. """
    biggest = 1   # default return if no actionstrips
    for strip in self.model.actionStrips:
      if strip.stripEnd > biggest:
        biggest = strip.stripEnd
    return biggest

class Diagnostics:
  """ Print summaries and test results to the console.
      Usage: Diagnostics()
      """

  def __init__(self):
    self.banner()
    self.summaries()
    self.run_tests()
    self.test_results()

  def summaries(self):
    print "=== summaries ==="
    self.scene_summary()
    print Model().summary()
    self.action_summary()

  def banner(self):
    print "\n\n"
    print "="*43
    iso_time = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
    # or just time.ctime()
    print "=== %s on %s === " % (script_name, iso_time)
    print "="*43

  def scene_summary(self):
    scene = bpy.data.scenes.active
    print " scene name is '%s'" % scene.name
    print " visible layers are '%s'" % str(scene.layers)

  def action_summary(self):
    print " bpy.data.actions: "
    for action in bpy.data.actions:
      print "  '%s' " % action.name

  def ok(self, assertion, message):
    """ Run a single test, printing 'ok' or 'not ok' and the message.
        Usage: diagnostics.ok(boolean_test, test_description) """
    status = ' not ok'
    self.tests_run += 1
    if assertion:
      status = ' ok'
      self.tests_ok += 1
    print " %-8s  %s " % (status, message)

  def test_results(self):
    print "=== Finished %i tests. ===" % self.tests_run
    if self.tests_ok == self.tests_run:
      print " All tests passed."
    else:
      n_failed = self.tests_run - self.tests_ok
      if n_failed==1:
        print " Failed 1 test."
      else:
        print " Failed %i tests." % n_failed

  def run_tests(self):
    """ The unit tests. """
    self.tests_run = 0
    self.tests_ok = 0
    print "=== Starting tests. ==="
    # --- start of tests --------------------------------------------------
    # ... ok infrastructure
    self.ok(1==1, "ok itself")
    # ... get()
    self.ok(get("mannequin").name=="mannequin", "get('mannequin')")
    self.ok(get("default action").name=="default action", 
            "  get('default action')")
    act1 = bpy.data.actions['step forward L to R']
    self.ok(get(act1).name=='step forward L to R', '  get(action)')
    s1 = Step('step forward L to R')
    self.ok(get(s1).name=='step forward L to R', '  get(Step())')
    get_blank = True
    try:
      get("")
    except:
      get_blank = False
    self.ok(not get_blank, "  get('') raises exception.")
    # ... blender_frame() ...
    Blender.Set('curframe', 1)
    self.ok(1 == blender_frame(), 'frame()')
    blender_frame(2)
    self.ok(2 == blender_frame(), '  frame(2)')
    # ... max_matrix() ...
    self.ok(max_matrix([[1,2,3],[-4,3,2]])==4, 'max_matrix()')
    # ... Step().bone_transform ...
    action_name = 'step back L to R'
    position = Mathutils.Vector(0.0, 4.91, 0.0)
    rotation = Mathutils.Quaternion(1,0,0,0) # no rotation
    transform = offset_and_rotation_to_matrix(position, rotation)
    motion = Step(action_name).bone_transform()
    # print " transform = '%s' " % str(transform)
    # print " motion = '%s' " % str(motion)
    max_diff = max_matrix(motion - transform)
    allowed_diff = 1.0e-3
    self.ok( max_diff < allowed_diff, "Step('%s').bone_transform()" % action_name)
    step1 = Step('forward')
    self.ok(step1.action.name=='step forward L to R', "  Step('forward')")
    step2 = Step('forward', 'L', mirror=True)
    self.ok(step2.action.name=='step back R to L', "  step mirrored")
    self.ok(Step.flip('forward')=='back', "  Step.flip()")
    # ... model ...
    man = Model("man")
    self.ok(man != None, "Model('man')")
    man.reset()
    self.ok(len(man.model.actionStrips)==1, "  reset() actionstrips")
    self.ok(len(man.model.ipo.curves[0].bezierPoints)==1, "  reset() ipo")
    frames = 12
    action_name = 'step forward L to R'
    man.add_motion(action_name, frames)
    ## print "  step   : '%s'" % str(step_L_to_R)
    ## print "   name  : '%s'" % step_L_to_R.action.name
    ## print "  strip1 : '%s'" % str(man.model.actionStrips[1])
    ## print "   name  : '%s'" % str(man.model.actionStrips[1].action.name)
    # actionstrip objects are different ... that surprized me.
    # but name is OK; I guess it makes a copy somewhere.
    # self.ok(man.model.actionStrips[1] == step_L_to_R, "  add_motion()")
    step_L_to_R = man.model.actionStrips[-1]
    self.ok(step_L_to_R.action.name == action_name, "  add_motion()")
    actual_frames = step_L_to_R.stripEnd - step_L_to_R.stripStart
    self.ok(actual_frames == frames, "    frame length")
    man.housekeeping()
    end0 = man.model.actionStrips[0].stripEnd
    self.ok(end0 == start_frame + frames, "  housekeeping() strip0")
    action_name_2 = 'step side R to L'
    man.add_motion(action_name_2, frames)
    man.housekeeping()
    blender_frame(25)
    self.ok(abs(man.model.LocY - (-1.007)) < 0.01, '  add_location moves obj')
    ## ...
    #  woman walking backwards ... used for manual testing
    if (False):
      woman = Model('woman')
      woman.reset()
      #    woman makes 3 steps; let's see if object follows backward motion
      #    ... looking at blender window, appears to work,
      #    but RotZ jumps between +180 and -180, 
      #    and ipo points are left selected.
      steps = ('step back L to R', 'step shift R to L', 'step back L to R')
      for s in steps:
        woman.add_motion(s, frames)
        woman.housekeeping()
    # ...
    # couple walk sequence 
    woman = Model('woman')
    seq = ['forward', 'side', 'shift', 'back', 'side', 'shift']
    man.walk_sequence('L', seq, woman)
    
   # --- end of tests ----------------------------------------------------
    
# Diagnostics()

class Tango:
  """ couple dance with man, woman models
      with walk sequence from a .steps file. """
  def __init__(self, filename=None):
    self.man = Model('man')
    self.woman = Model('woman')
    self.filename = filename
