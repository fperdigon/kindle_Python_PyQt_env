import gtk, cairo, gobject
import random, math
 
class Screen( gtk.DrawingArea ):
 
 def __init__(self):
 super(Screen,self).__init__()
 self.connect ( "expose_event", self.do_expose_event )
 gobject.timeout_add( 10, self.tick )
 self.set_size_request(200,200)
 
 def tick ( self ):
 self.alloc = self.get_allocation ( )
 rect = gtk.gdk.Rectangle ( self.alloc.x, self.alloc.y, self.alloc.width, self.alloc.height )
 self.window.invalidate_rect ( rect, True )
 return True
 
 def do_expose_event( self, widget, event ):
 self.cr = self.window.cairo_create( )
 self.draw( *self.window.get_size( ) )
 
class Stuff (Screen):
 
 def __init__ ( self ):
 Screen.__init__( self )
 rect = self.get_allocation()
 self.x = rect.x + rect.width / 2
 self.y = rect.y + rect.height  / 2
 self.X = 0
 self.Y = 0
 self.incX = 1
 self.incY = 1
 self.ball_size = 5
 self.stick_len = 50
 self.L_posX = 0
 self.L_posY = 0
 self.R_posX = 0
 self.R_posY = 0
 self.connect('key-press-event', self.on_key_press)
 self.connect('key-release-event', self.on_key_press)
 
 def on_key_press(self,  widget, event, *args):
 """handle keyboard events"""
 
 keyname = gtk.gdk.keyval_name(event.keyval)
 if event.type == gtk.gdk.KEY_PRESS:
 if keyname == 'a'  and self.stick_len / 2 - self.L_posY < self.y  :
 self.L_posY -= 15
 if keyname == 'z' and self.stick_len / 2+ self.L_posY < self.y :
 self.L_posY += 15
 
 return False
 
 def draw( self, width, height ):
 cr= self.cr
 matrix = cairo.Matrix ( 1, 0, 0, 1, width/2, height/2 )
 cr.transform ( matrix )
 self.drawcross ( cr )
 self.drawpoint(cr)
 self.drawstick_left(cr)
 self.ball_L ( cr)
def drawcross ( self, cr ):
 
 rect  = self.get_allocation ( )
 size = rect.width
 self.x = rect.x + rect.width / 2
 self.y = rect.y + rect.height  / 2
 cr.set_source_rgb ( 0, 0, 0 )
 cr.move_to ( 0 , 0)
 cr.line_to ( 0, size )
 cr.move_to ( 0, 0)
 cr.line_to ( 0,-size )
 cr.move_to ( 0, 0 )
 cr.line_to ( -size, 0 )
 cr.move_to ( 0, 0 )
 cr.line_to ( size, 0 )
 cr.set_dash([10, 20], 0)
 cr.stroke ( )
 
 def drawpoint (self, cr ):
 
 rect = self.get_allocation ( )
 x = rect.x + rect.width / 2
 y = rect.y + rect.height  / 2
 
 if abs(self.X) > rect.width - x :
 #change direction
 self.incX = -self.incX
 if abs(self.Y) > rect.height - y :
 #change direction
 self.incY = -self.incY
 self.X += self.incX
 self.Y += self.incY
 
 cr.arc(  self.X  , self.Y, self.ball_size, 0  , 2 * math.pi)
 cr.set_line_width(10)
 cr.set_source_rgb ( 0, 1, 0 )
 cr.fill()
 
 def drawstick_left (self, cr):
 
 rect = self.get_allocation ( )
 x = rect.x - rect.width   / 2
 y = rect.y + rect.height  / 2
 self.L_posX = x  + 20
 cr.move_to(self.L_posX   , self.L_posY - self.stick_len / 2)
 cr.line_to(self.L_posX      , self.L_posY + self.stick_len / 2 )
 cr.set_line_width(10)
 cr.set_source_rgb ( 1, 0, 0 )
 cr.set_dash([1, 0], 0)
 cr.stroke()
 
 def ball_L (self, cr) :
 if self.X == self.L_posX   :
 if abs( self.Y - self.L_posY   )  < self.stick_len / 2:
 self.incX = -self.incX
 
def run( Widget ):
 window = gtk.Window( )
 window.connect( "delete-event", gtk.main_quit )
 widget = Widget( )
 window.connect('key-press-event' , widget.on_key_press)
 widget.show()
 window.add( widget )
 window.present( )
 gtk.main( )
 
run( Stuff )
 
