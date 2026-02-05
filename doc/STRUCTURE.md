# Architecture Overview - Powers of Ten Viewer

## Component Responsibilities

```
┌─────────────────────────────────────────────────────────────────┐
│                         VIEWER.PY                               │
│                     (Main Coordinator)                          │
│  • Owns all components                                          │
│  • Runs game loop                                               │
│  • Delegates to specialists                                     │
└─────────────────────────────────────────────────────────────────┘
         │
         ├──────────┬──────────┬──────────┬──────────┬──────────
         ▼          ▼          ▼          ▼          ▼          ▼
    ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
    │ Image  │ │  Zoom  │ │Transi- │ │Render- │ │ Input  │ │ Pygame │
    │Manager │ │Control │ │tion    │ │  er    │ │Handler │ │ Screen │
    │        │ │  ler   │ │Manager │ │        │ │        │ │        │
    └────────┘ └────────┘ └────────┘ └────────┘ └────────┘ └────────┘
```

### Components

1. **`image_manager.py`** 
   - `ImageData`: Encapsulates image data
   - `ImageManager`: Loads and manages images
   - Responsibility: Image loading, scaling, and metadata

2. **`zoom_controller.py`** 
   - `ZoomController`: Manages zoom state and animations
   - Responsibility: All zoom logic (step, continuous, boundaries)

3. **`transition_manager.py`** 
   - `TransitionManager`: Handles transition animations
   - Responsibility: Loading and playing transition frames

4. **`renderer.py`** 
   - `Renderer`: Handles all drawing
   - Responsibility: Rendering images, transitions, UI, crop optimization

5. **`input_handler.py`** 
   - `InputHandler`: Processes keyboard input
   - Responsibility: Event processing, key timing

6. **`viewer.py`** 
   - `ZoomViewer`: Main coordinator
   - Responsibility: Initializing components and running game loop

## Benefits

✅ **Single Responsibility**: Each class has one clear purpose
✅ **Open/Closed Principle**: Easy to extend without modifying existing code
✅ **Testable**: Each component can be tested independently
✅ **Maintainable**: Know exactly where to look for specific functionality
✅ **Reusable**: Components can be used in other projects

## Detailed Responsibilities

### 1. **ImageManager** (image_manager.py)
**"I know about images and their properties"**

```python
Responsibilities:
├─ Load images from config
├─ Calculate max_scale for each image
├─ Store image surfaces (original + scaled)
├─ Get rect coordinates (pixel → relative conversion)
├─ Track current image index
└─ Navigate between images (next/previous)

Data it owns:
├─ List of ImageData objects
│   ├─ original surface
│   ├─ scaled surface  
│   ├─ max_scale
│   └─ scale_factor
├─ Current image index
└─ Config data

Does NOT:
✗ Know about zoom state
✗ Handle rendering
✗ Process input
```

### 2. **ZoomController** (zoom_controller.py)
**"I manage zoom state and animations"**

```python
Responsibilities:
├─ Track current scale value
├─ Animate zoom transitions (start_scale → target_scale)
├─ Handle zoom in/out requests
├─ Continuous zoom (time-based)
├─ Check if scale exceeded boundaries
└─ Update scale each frame

Data it owns:
├─ current scale
├─ target_scale
├─ start_scale
├─ is_zooming (animation state)
├─ zoom_start_time
└─ min_scale (always 1.0)

Does NOT:
✗ Know what image is displayed
✗ Handle rendering
✗ Process keyboard input directly
```

### 3. **TransitionManager** (transition_manager.py)
**"I play transition animations between images"**

```python
Responsibilities:
├─ Load transition frames from disk
├─ Scale frames to viewport
├─ Play animation forward/backward
├─ Track animation progress
└─ Know when transition is complete

Data it owns:
├─ List of transition frames
├─ Current frame index
├─ Direction (forward/backward)
├─ Is active flag
├─ Frame timing (FPS, duration)
└─ Viewport dimensions

Does NOT:
✗ Know about image content
✗ Handle zoom state
✗ Process input
```

### 4. **Renderer** (renderer.py)
**"I draw everything to the screen"**

```python
Responsibilities:
├─ Draw zoomed images with crop optimization
├─ Calculate anchor points for smooth zoom
├─ Draw transition frames
├─ Draw bounding rectangles
├─ Draw UI text (instructions, FPS)
└─ Handle viewport → screen blitting

Data it owns:
├─ Viewport surface
├─ Viewport rect (position on screen)
├─ Screen surface
└─ Font

Uses (read-only):
├─ ImageManager.get_current_image()
├─ ZoomController.scale
├─ TransitionManager.get_current_frame()
└─ Config data

Does NOT:
✗ Modify zoom state
✗ Modify image index
✗ Process input
```

### 5. **InputHandler** (input_handler.py)
**"I translate keyboard events into actions"**

```python
Responsibilities:
├─ Process pygame events
├─ Detect key presses (with debouncing)
├─ Track continuous zoom keys
└─ Return simple commands

Data it owns:
├─ Key press timestamps (for debouncing)
├─ Continuous zoom state
└─ Key delay threshold

Returns:
├─ 'quit' | 'zoom_in' | 'zoom_out' | None
└─ continuous_zoom state

Does NOT:
✗ Execute zoom logic
✗ Change images
✗ Know about scale values
```

---

## Use Case Flow Examples

### **Use Case 1: User presses UP key to zoom in**

```
┌─────────────┐
│   VIEWER    │ Game loop running
└──────┬──────┘
       │
       ├─► InputHandler.handle_input()
       │   ├─ Detects UP key press
       │   ├─ Checks debounce timing
       │   └─ Returns 'zoom_in'
       │
       ├─► ZoomController.zoom_in(max_scale)
       │   ├─ Calculates new target_scale (current * 1.15)
       │   ├─ Sets start_scale = current scale
       │   ├─ Sets is_zooming = True
       │   └─ Records zoom_start_time
       │
       ├─► ZoomController.update(dt)  [called every frame]
       │   ├─ Calculates animation progress
       │   ├─ Interpolates scale: start → target
       │   └─ Updates current scale
       │
       ├─► ZoomController.check_boundaries(max_scale)
       │   ├─ Checks if scale > max_scale
       │   └─ Returns 'next_image' if exceeded
       │
       ├─► ImageManager.next_image()  [if boundary exceeded]
       │   ├─ Increments current_index
       │   └─ Returns new image data
       │
       ├─► TransitionManager.start('forward')
       │   ├─ Sets is_active = True
       │   ├─ Sets direction = 'forward'
       │   └─ Resets frame_index
       │
       ├─► TransitionManager.update(dt)  [called every frame]
       │   ├─ Increments frame based on time
       │   └─ Returns current transition frame
       │
       └─► Renderer.draw(...)
           ├─ If transitioning: draws transition frame
           └─ Else: draws zoomed image with crop optimization
```

### **Use Case 2: Rendering a zoomed image**

```
┌─────────────┐
│  RENDERER   │ draw() called
└──────┬──────┘
       │
       ├─► ImageManager.get_current_image()
       │   └─ Returns current ImageData
       │
       ├─► ImageManager.get_rect(current_index)
       │   ├─ Gets rect from config
       │   ├─ Converts pixel → relative coords
       │   └─ Returns normalized rect
       │
       ├─► ZoomController.get_scale()
       │   └─ Returns current scale value
       │
       ├─► Calculate anchor points
       │   ├─ Determine rect's relative position
       │   ├─ Calculate image anchor point
       │   ├─ Calculate rect anchor point
       │   └─ Interpolate focus point based on zoom
       │
       ├─► Choose rendering path
       │   ├─ If scale < 1.5: Simple scale
       │   └─ If scale >= 1.5: Crop optimization
       │
       ├─► Crop optimization path:
       │   ├─ Calculate visible region
       │   ├─ Map to original image coords
       │   ├─ Subsurface crop from original
       │   └─ Scale only the cropped portion
       │
       ├─► Position calculation
       │   ├─ Apply anchor point alignment
       │   └─ Adjust for crop offset
       │
       └─► Blit to viewport → screen
           ├─ Draw scaled image
           ├─ Draw bounding rect
           └─ Draw UI text
```

### **Use Case 3: Playing transition animation**

```
┌─────────────┐
│   VIEWER    │ Zoom exceeded boundary
└──────┬──────┘
       │
       ├─► ZoomController.check_boundaries()
       │   └─ Returns 'next_image'
       │
       ├─► TransitionManager.start(direction)
       │   ├─ Sets is_active = True
       │   ├─ Sets direction ('forward' or 'backward')
       │   ├─ Resets frame_index = 0
       │   └─ Records start_time
       │
       ▼
   [Every frame while transitioning]
       │
       ├─► InputHandler.handle_input()
       │   ├─ If transition active: blocks input
       │   └─ Returns None
       │
       ├─► TransitionManager.update(dt)
       │   ├─ Calculates target_frame from elapsed time
       │   ├─ If backward: reverses frame order
       │   └─ Increments frame_index
       │
       ├─► TransitionManager.is_complete()
       │   ├─ Checks if all frames played
       │   └─ Returns True/False
       │
       ├─► If complete:
       │   ├─► ImageManager.next_image()  [or previous]
       │   │   └─ Updates current_index
       │   │
       │   ├─► ZoomController.reset()
       │   │   └─ Sets scale = min_scale or max_scale
       │   │
       │   └─► TransitionManager.stop()
       │       └─ Sets is_active = False
       │
       └─► Renderer.draw()
           ├─ Checks TransitionManager.is_active()
           ├─ Gets TransitionManager.get_current_frame()
           └─ Draws transition frame (ignores zoom)
```

---

## Data Flow Diagram

```
┌──────────────────────────────────────────────────────────┐
│                    READ-ONLY DATA                        │
│  config.json ──► ImageManager (loads images)             │
│  sample transitions/ ──► TransitionManager (loads frames)│
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│                   MUTABLE STATE (Owned)                  │
│                                                           │
│  ImageManager:          ZoomController:                  │
│  • current_index        • scale                          │
│  • images[]             • target_scale                   │
│                         • is_zooming                     │
│  TransitionManager:                                      │
│  • is_active            InputHandler:                    │
│  • frame_index          • key_timestamps                 │
│  • direction            • continuous_zoom                │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│                  STATELESS (Pure Logic)                  │
│                                                           │
│  Renderer:                                               │
│  • draw() - uses data from other components              │
│  • No internal state, just transforms data to pixels     │
└──────────────────────────────────────────────────────────┘
```

---

## Why This Design Prevents Mixing

### **Single Source of Truth**
- **Scale value**: Only ZoomController owns it
- **Current image**: Only ImageManager owns it
- **Transition state**: Only TransitionManager owns it

### **One-Way Dependencies**
```
Viewer ──► All components (owns them)
Renderer ──► Reads from all (never modifies)
Components ──X── Don't know about each other
```

### **Clear Interfaces**
```python
# ImageManager interface
get_current_image() → ImageData
get_rect(index) → pygame.Rect
next_image() → void
previous_image() → void

# ZoomController interface
zoom_in(max_scale) → void
zoom_out() → void
update(dt) → void
check_boundaries(max_scale) → 'next_image' | 'previous_image' | None
get_scale() → float

# TransitionManager interface
start(direction) → void
update(dt) → void
is_active() → bool
get_current_frame() → Surface
is_complete() → bool

# InputHandler interface
handle_input() → 'zoom_in' | 'zoom_out' | 'quit' | None
handle_continuous_zoom(dt) → bool

# Renderer interface
draw(image_data, scale, rect, transition_frame) → void
```

### **No Shared State**
Each component only modifies its own data. Communication happens through:
- **Method calls** (Viewer → Components)
- **Return values** (Components → Viewer)
- **Read-only queries** (Renderer → Components)

This prevents bugs like:
- ✗ Renderer accidentally changing zoom state
- ✗ InputHandler modifying images
- ✗ ZoomController triggering transitions
- ✗ Multiple sources of truth for scale value