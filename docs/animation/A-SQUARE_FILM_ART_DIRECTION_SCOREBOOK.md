# A-Square — Film Art Direction Scorebook
## Shariatpur riverfront, Delta Command, original name reveal and UI hand-offs

**Document type:** detailed visual treatment, shot choreography and production prompt scorebook  
**Revision:** 27 November 2026  
**Authoring target:** Blender 5.2.5 LTS  
**Runtime target:** Godot 4.4.1 Android  
**Visual objective:** original, Bangladesh-rooted premium game cinematics  
**Status:** art-direction specification; not a claim that the current render is approved

This scorebook is a companion to \`ASQUARE_CINEMATIC_ART_ANIMATION_BIBLE.md\`. The bible defines the quality contract. This file describes what the viewer should actually experience, moment by moment, and what the art team must create to produce that experience.

The visual references named in the project are references for craft: the confidence of a major game reveal, the legibility of a mobile-game lobby, the emotion of animated-film acting, the material richness of a premium environment, and the rhythm of an authored trailer. A-Square must make its own images. Do not reproduce another game's logo, character, map, title animation, interface, shot sequence or signature visual effect. A-Square's identity is the delta, the river, the everyday life of Bangladesh, and the people who inhabit it.

---

# PART I — THE FILMMAKER'S CONTRACT

## 1. The frame is a painting before it is a simulation

A shot is not a screenshot of a level. It is a composition with intention. The foreground, middle distance and far distance each have a job. The frame has a dominant shape, a directional flow, a point of rest and a place for the eye to travel. The viewer should not need to inspect the image to understand what matters.

Every shot must answer five questions before modelling begins:

1. What does the viewer notice first?
2. What should the viewer discover second?
3. What emotion should the image create?
4. What moves, and why does it move at this exact moment?
5. What changes in the viewer's understanding by the end of the shot?

A beautiful environment with a tiny, unreadable hero is still a failed hero shot. A detailed operator standing without intention is still a mannequin. A river that reflects the entire world like a perfect mirror is not convincing water. A camera that continuously moves without revealing anything is not cinematic movement.

The image must remain readable on a phone. The art team may use dense offline sculpts, exceptionally detailed source meshes, layered textures, decals, hand-painted masks, geometry nodes, rigged secondary elements and many millions of triangles where the offline authoring hardware permits. High polygon count is an available tool, not the goal. The goal is that the resulting silhouette, surface and light behave like a designed work of art.

## 2. The art hierarchy

### 2.1 Emotional hierarchy
The emotional subject outranks all decoration. The operator's face, a vehicle crossing the light, a ferry moving through a reflection, or the title mark should own the viewer's attention. Every other element supports, contrasts or frames that subject.

### 2.2 Silhouette hierarchy
A silhouette must be legible before its texture is visible. The operator's helmet, shoulder line, vest, weapon, hands and stance must separate from the background. The CNG canopy must read as a three-wheeler canopy, not a green box. The launch must have a recognisable hull and cabin. A banyan tree must read as a living branching canopy rather than a cluster of identical spheres.

### 2.3 Material hierarchy
Skin is not painted plastic. Cloth is not concrete with a fabric colour. Metal is not universally mirror-shiny. Glass is not a cyan slab. Water is not a blue plane. Every material requires a distinct response to broad light, grazing light, roughness variation, tiny surface detail and reflected shapes.

### 2.4 Spatial hierarchy
The camera needs a near object, a middle-distance story and a far environment. Parallax is an artistic resource. A foreground rope, leaf or mooring post can slide across the frame while the far bank drifts slowly, giving the viewer a strong sense of space. The camera must not be forced to show every part of the set at once.

### 2.5 Motion hierarchy
Motion is a performance with an intention, a beginning, a decision, an action, a reaction and a held finish. Physics helps the motion feel grounded, but animation is allowed to shape timing for emotion and readability. A head may notice something before the torso moves. A strap may lag after the body stops. A vehicle may settle after braking. A boat wake may continue after the hull passes. A cinematic camera may accelerate more quickly than a real camera would if that produces a clearer reveal.

## 3. Artist-first modelling rules

Do not build a large scene by repeating a box and changing its dimensions. Do not build an operator by changing only the colour of one suit. Do not add a hundred rings, cylinders or glowing rails because the frame looks empty. Each hero object must have a designed silhouette, construction logic, material transitions and a reason to exist.

For every hero model, the modelling pass should include:

- a silhouette block-out judged in flat black;
- primary forms designed as a coherent object, not a pile of primitives;
- secondary forms that explain use, construction, wear and ergonomics;
- tertiary details that reward close views without becoming noise;
- high-resolution surface treatment, roughness breakup, normal detail and deliberate edge treatment;
- hand-authored imperfections, asymmetry and irregularities;
- proper pivot placement, rig hierarchy and naming for animation;
- a neutral-light turntable review and a final cinematic-light review.

Use sculpting, bevelled/curved surfaces, retopology, weighted normals, subdivision, displacement, trim sheets, decals, vertex painting and custom shader work where they help. A procedural node network is a tool for building a surface; it is not an excuse to avoid artistic judgement. A procedural result still requires a selected scale, palette, contrast, texture density and wear story.

## 4. What must not be accepted

Reject a scene when its subject is too small to read, when the camera sees through washed-out glass, when repeated facades become a wallpaper pattern, when the lighting removes form, when every object is equally sharp, when reflections are decorative rather than environmental, when the operator's pose looks frozen, when the CNG moves without believable wheel/contact behaviour, or when the title is a generic spinning primitive.

A green source test is not a visual approval. A successful Blender render is not an Android approval. A valid GLB is not a good character. A large download is not evidence of a premium environment. Every gate is separate.

---

# PART II — SEQUENCE A: SHARIATPUR RIVERFRONT LOGIN FILM

## 5. The emotional premise

The player is not entering a generic shooter menu. The player is arriving at a place. The river has carried boats, work, commerce, weather and memory through this landscape. The road is close to the water. The town is ordinary and recognisable rather than a theme park of monuments. The operator is not waiting on a podium; the operator belongs to the world and is about to invite the player into it.

**Target duration:** 12 seconds at 24 frames per second  
**Primary emotional movement:** place → life → discovery → human connection → identity  
**Palette:** late-afternoon amber, river teal, weathered lime, deep foliage, muted brick, charcoal asphalt and controlled warm highlights  
**Primary motion:** river, launch, CNG and the operator's eyes/head/shoulders  
**Secondary motion:** foliage, cloth, straps, cables, ripples, reflections, haze and distant life  
**Final state:** a clean, readable A-Square title and a calm Continue/Login hand-off

The film should not show all the props in one frame. It should reveal the location in layers, like a director guiding a viewer through an actual place.

## 6. Shot A1 — River establishes the world

**Time:** 00:00–00:02.4  
**Frames:** 1–58  
**Lens language:** a wide but not distorted establishing lens; preserve verticals and the horizon  
**Dominant subject:** the river bend, near-bank ghat and the settlement beyond

### Image description
Begin close to the waterline, not from an abstract top-down view. A soft near-foreground shape—mooring rope, wet stone, a timber post or the out-of-focus edge of a boat—frames one lower corner. The river occupies the lower and middle portions of the image. Across it, the far bank and low structures sit in atmospheric distance. The near ghat rises into frame at an angle, giving a clear route for the eye to travel from water to steps to street to buildings and sky.

The horizon is visible but not an empty line. Far-bank landforms, trees, roofs and a distant vessel break the silhouette. The settlement is recognisably Bangladeshi through roof tanks, rooftop additions, modest mixed-use blocks, balcony rails, signs, awnings, trees and electrical lines. It is not a generic European waterfront and not an exaggerated fantasy skyline.

### Camera choreography
The camera begins almost still, then performs a slow lateral truck with a very slight forward drift. The water slides past the foreground at a perceptible speed; the far bank barely moves. The ghat steps reveal themselves in parallax. The camera does not tilt up simply to show more sky. Its motion exposes a path into the town.

At the final third of the shot, a small glint travels across one wave crest. The glint is motivated by the sun direction; it is not an emissive neon stripe. The camera reaches a deliberate pause before the next subject enters.

### Water and shoreline
The river needs layered wave lengths. Broad swell should be slow and low. Mid-scale wavelets should catch grazing light. Fine ripples should break large reflections into uneven fragments. The shoreline must show damp stone, darker wet edges, algae in creases, soft deposits, old stains, uneven mortar and places where water has touched the steps repeatedly.

The reflection is not a perfect copy of the sky. It is a distorted image of light and architecture, stretched and broken by the water's changing normal. Reflections of bright structures can appear in the water, but they should bend, narrow, fragment and lose detail with distance and surface angle. The near water may show broad copper/teal highlights; farther water becomes quieter and less contrasty.

### Sound direction (for a later licensed/original audio pass)
Start with a low, open river ambience: soft water against stone, a distant engine, a few birds, a far-off human murmur. Do not fill the opening with explosions, synthetic risers or a generic military drum hit. The first sound should make the place feel inhabited.

### Rejection conditions
Reject the shot if the river reads as a rectangular blue floor, if the ghat is just five identical steps, if the far bank is absent, if the near foreground blocks the water, or if the camera movement has no parallax.

## 7. Shot A2 — The settlement breathes

**Time:** 00:02.4–00:04.5  
**Frames:** 59–108  
**Lens language:** medium-wide perspective; buildings retain individual profiles  
**Dominant subject:** a small section of ordinary riverside street, with one recognisable shopfront and a passing CNG entering as secondary action

### Image description
The camera moves closer to the street rather than teleporting to a disconnected view. A weathered shopfront enters from one side: painted signboard, fabric awning, metal shutter or open service counter, a few shelves visible inside, a concrete ledge, old wiring and a small light. Beside it, another building has a different floor rhythm, balcony depth, colour, roof shape and pattern of openings. Their difference must be structural, not merely a different albedo.

The road has real depth. A curb, drainage edge, worn surface, patched repair, puddle or tire mark provides scale. A tree canopy crosses part of the top frame and casts soft patterned shade. The camera should glimpse the river behind or between structures rather than losing all geography.

### CNG entrance and performance
The CNG enters with a clear screen direction and a readable silhouette. Its canopy has a designed curve and edge piping. The windscreen is an aperture with a frame and reflections, not a flat translucent panel. The passenger space has a bench, grab rail and floor. The front nose, mudguard, fender and wheel relationship must be proportionally coherent. Lamps, plate, canopy supports and trim must be placed like a real vehicle.

The vehicle decelerates slightly as it passes the camera's chosen mark. The front wheels respond to steering; wheel rotation matches travel; the body settles through suspension rather than bobbing vertically at a constant rhythm. Its painted surfaces carry subtle dust, scratches, polish on hand-contact areas and uneven fading. Tyres are matte and worn, not shiny black plastic.

### Character and environment continuity
Do not allow the CNG to hide the eventual operator. It can occupy the foreground for a moment, then exit sufficiently to expose a human silhouette or the operator's location. Any background NPC must have a readable role—shopkeeper turning toward the road, passer-by shifting weight, or someone seated at the shop edge. If a background person is too small, let them read as a deliberate silhouette, not a half-modelled mannequin.

### Rejection conditions
Reject if the CNG looks like a geometric toy, if its wheels do not relate to its travel, if storefronts repeat like identical modular units, or if the vehicle masks the hero.

## 8. Shot A3 — Launch, wake and reflected light

**Time:** 00:04.5–00:06.7  
**Frames:** 109–160  
**Lens language:** compressed medium shot with a foreground waterline  
**Dominant subject:** a small local launch gliding over the river

### Image description
The camera sees the launch at an angle, not as a flat side-view diagram. The hull has a recognisable bow, stern, waterline and deck profile. The cabin is a built object with glazing, frame thickness, posts, doors, roof edge, rails, bumpers and signs of regular use. The paint is not uniform. Sun-facing surfaces are warmer; shaded surfaces are cooler; contact edges are rubbed; dark recesses collect grime.

A rope or fender hangs with gravity and responds softly to the hull's movement. A passenger silhouette or crew detail can be present only when it is clear enough to read. The ferry/launch has weight; it does not skate over the water.

### Motion design
The launch glides, yaws by a few degrees and responds to a gentle current. It rises and falls with a low, irregular buoyant motion. The hull creates a tapered wake that begins near the stern and spreads asymmetrically. The wake has layered foam and ripple detail that breaks apart over time. It must not be a set of rigid white wires or repeated circles.

The river reacts: a moving highlight stretches and breaks around the hull, the wake disturbs the water's larger wave pattern, and the reflection of the cabin is pulled into irregular vertical fragments. The reflections should change from frame to frame as the launch moves.

### Camera movement
A controlled tracking move matches the launch for a brief beat, then eases away to show its relation to the ghat and far bank. Use focus deliberately: foreground ripple or rope may soften as the launch becomes sharp, then a far-bank light or building edge briefly resolves.

### Rejection conditions
Reject if the hull has no real wake, if the reflection looks pasted on, if the launch has no mass, or if camera tracking loses the vessel.

## 9. Shot A4 — The operator becomes a person

**Time:** 00:06.7–00:09.4  
**Frames:** 161–226  
**Lens language:** portrait/medium close-up with restrained compression  
**Dominant subject:** the Field Ranger's face, upper body, gear and gaze

### Image description
Move into a three-quarter portrait. The operator is large enough to read at phone scale. The background becomes a designed bokeh of river light, tree shade and distant architecture, rather than a blank empty plane. There is a clear outline around helmet, shoulder, vest and weapon. Face, skin, eyes and uniform receive the strongest material scrutiny in the entire login film.

The actor should not simply stare at the camera. Begin with attention slightly away from the viewer. An environmental cue is noticed. The eyes shift first. The head follows by a smaller amount. The neck and shoulder settle after the head. The torso subtly changes weight as the operator prepares to engage with the viewer. Then the gaze meets the lens and holds.

### Body performance
Breathing changes the chest/abdomen and produces a tiny shoulder movement. One shoulder carries slightly more equipment weight. The hands are not perfectly mirrored; each has a different role and tension. Fingers keep contact with the weapon or sling. The elbow line is purposeful. The feet and pelvis establish support even when the portrait hides the lower body.

Straps and loose pouches lag after the torso's small shift. Cloth folds compress near the elbow and waist; they do not simply ripple like water. The helmet fit, ear protection, chin strap, glove, wrist, vest panels, webbing and weapon grip are reviewed independently.

### Light and surface
Use a soft warm key from the sun direction, a cool sky fill that keeps the shadow eye readable, and a narrow rim that separates helmet/shoulder from the dark background. Avoid blowing the forehead, washing out the nose or turning the skin waxy. Skin has restrained subsurface scattering, tonal variation, pore/roughness detail and a natural specular response. Eyes need wetness, catchlights, iris/pupil detail and a believable lid line. Cloth and webbing remain rougher than skin and painted metal.

### Acting hold
The final gaze is held long enough for a human connection. It is not a generic idle loop. A tiny breath, one controlled blink or a small shift in focus is enough. Avoid continuous head shaking, exaggerated scanning or constant movement that steals attention.

### Rejection conditions
Reject if the operator occupies too little of the frame, if the face is unreadable, if the actor swivels like a mannequin, if hands float, if the weapon intersects the body, or if every strap moves in synchrony.

## 10. Shot A5 — The delta mark and title resolve

**Time:** 00:09.4–00:12.0  
**Frames:** 227–288  
**Lens language:** composed final frame, readable title  
**Dominant subject:** original A-Square delta mark and wordmark, with the operator and place retained as context

### Design
The logo is an original piece of art. It can be inspired by the braided paths of rivers and the branching outline of a delta, but it must be designed as a memorable compact silhouette. It is not a stack of spinning primitives. Its form may be machined metal, a subtle etched inlay, a designed light trace, painted enamel or a crafted graphic mark.

The mark enters through a clear visual event. A highlight travels along one river-like contour. The second contour follows with a slight delay. The main shape resolves as the two paths meet. The wordmark appears with measured spacing and a restrained material response. A small river-line accent may settle underneath.

### Motion
The mark has anticipation, reveal, overshoot and settle. The initial light trace accelerates, then slows near the key intersection. The emblem may grow slightly beyond its final size and settle once; it must not wobble repeatedly. A small particle or water droplet accent can drift past, but no generic sparkle cloud. The title holds steady for reading.

### UI hand-off
The login panel should not suddenly cover the film. The camera finishes its movement; the title settles; the background grade dims or shifts subtly; then the user interface enters with a deliberate material/opacity/position transition. The Continue/Login action is clearly available. The film may be interrupted by a user tap without forcing the user to wait. All progress, authentication and loading states are real application state, not simulated decoration.

### Rejection conditions
Reject if the title is too small, if the mark looks like an arbitrary ring, if it hides the operator, or if the login panel appears as an unrelated overlay.

---

# PART III — SEQUENCE B: DELTA COMMAND OPERATOR LOBBY

## 11. The emotional premise

The lobby is a staffed place, not a showroom. The three operators are distinct people with separate roles, anatomy, faces, posture, kit and acting. The hall's scale establishes capability, but the architecture must frame the operators rather than compete with them. This is the point at which the player chooses who will carry them into the next mode.

**Target duration:** 12 seconds at 24 frames per second  
**Primary emotional movement:** anticipation → architecture → three identities → selected hero → interactive choice  
**Palette:** graphite and deep river teal; warm tungsten task pools; cool river fill; small red/amber operational accents  
**Primary motion:** camera reveal, three different operator performances, live displays and ferry outside  
**Secondary motion:** fan, cables, screen updates, reflections, a far staff silhouette and subtle equipment response  
**Final state:** selected operator, name/role information and functional lobby controls

The current environment should not preserve a large glass wall or structural pillar in a position that makes the operators tiny or visually washed out. If the camera needs to be inside the building, place it inside. If the front glazing blocks the characters, redesign the viewing axis or remove the obstructing pane from the shot—not the character from the composition.

## 12. Shot B1 — Enter the command hall

**Time:** 00:00–00:02.0  
**Frames:** 1–48  
**Lens language:** wide, architectural, controlled perspective  
**Dominant subject:** the command hall opening toward the river

### Image description
Start behind one near structural edge, a dark truss, a console corner or a cropped equipment case. The viewer sees only a portion of the hall. The camera glides laterally and the interior opens. The floor, ceiling and glass create converging lines toward the operator area. The river is visible beyond the hall but does not overpower the interior.

The architecture has a rhythm and purpose: steel ribs, glass panels with proper mullions, transoms, braces, roof trusses, cable trays, ventilation, light baffles, equipment bays, floor transitions, scuffed corners and acoustic surfaces. It should feel like a building that someone designed, built, used and maintained—not a futuristic warehouse assembled from identical rectangles.

### Light
Keep the outside river cool and the interior slightly warmer. The daylight entering through the glass should create directional pools and reflections, but it must not overexpose the scene or wash every operator in cyan. Light sources need believable size, position, falloff and shadow behaviour.

### Camera
The shot may include a short rack focus from the foreground structure to the operator area. The camera should settle with the three operators becoming clearly visible. Do not orbit around the hall without purpose.

## 13. Shot B2 — Field Ranger portrait

**Time:** 00:02.0–00:03.6  
**Frames:** 49–86  
**Lens language:** medium portrait, slightly low camera height  
**Dominant subject:** Field Ranger

### Acting direction
Field Ranger carries calm frontline readiness. The weapon sits in a low-ready position with shoulder/hand/stock contact; the muzzle direction is safe and intentional. The feet carry weight. The torso is relaxed but not slumped. Gaze begins just off axis, checks the room, then returns to a steady forward focus.

The actor has a small inhale, subtle chest movement and a tiny head correction. A strap settles after the shoulder moves. Fingers maintain a believable grip. One elbow leads slightly, producing a natural asymmetry. Do not make the actor continuously rotate the gun or bounce in place.

### Composition
The helmet and shoulders create a recognisable silhouette. The face and gear must be visible. The background display may be defocused but its graphics should suggest a real operational map or status wall, not random glowing rails. The light on the operator is warmer than the river behind him, and the rim catches the edge of the helmet and vest without turning them into a glowing cutout.

## 14. Shot B3 — Delta Recon portrait

**Time:** 00:03.6–00:05.2  
**Frames:** 87–124  
**Lens language:** medium close-up, controlled lateral movement  
**Dominant subject:** Delta Recon

### Acting direction
Delta Recon's performance is not Field Ranger played in a different costume. Her posture, face, equipment silhouette and gesture are different. She has a recon specialist's attentive precision. Her head angle is slightly different, shoulders carry another line, and the kit's weight distribution is unique.

The eyes inspect a screen or a distant point. The head follows after a brief delay. The torso makes a small compensating adjustment. The pistol/weapon grip remains secure; fingers do not merge with the prop. One hand may briefly check a strap or device, provided the source animation can be edited to maintain exact contact.

Her idle is composed rather than robotic. A blink, breath and tiny weight shift punctuate the shot. Cornrows/hair, helmet or headwear, face and blue-grey kit must be distinct and properly fitted. This operator must not appear to be a recoloured Field Ranger.

### Composition
Give the face enough size to read. Use a different angle and lighting pattern from the previous portrait. A cool display reflection may catch the side of the face, while a warm fill maintains skin tone. Background lines should not intersect the head silhouette.

## 15. Shot B4 — River Scout portrait

**Time:** 00:05.2–00:06.8  
**Frames:** 125–162  
**Lens language:** medium portrait with a slightly longer focal length  
**Dominant subject:** River Scout

### Acting direction
River Scout reads as an experienced older scout. His heavier body proportions and different facial hair produce another shape before the viewer notices the colour of his clothes. His posture carries weight through hips and shoulders. He scans toward the riverfront with a measured head turn. The body follows only slightly. He takes a controlled breath and settles. His gear is arranged for the role and the environment; it is not a mirrored copy of the other two operators.

The tan river-country kit uses different wear patterns and fabric response. The vest, belt and pouches are laid out differently. Equipment hangs and settles according to weight. A heavier body does not bounce like a lightweight mannequin.

### Composition
Let his shoulder line and head profile occupy a different portion of the frame. The lens compression should make the face/gear feel substantial. A soft warm light catches facial hair and the edge of the vest; cool river light separates the far side.

## 16. Shot B5 — The three-person composition

**Time:** 00:06.8–00:09.2  
**Frames:** 163–220  
**Lens language:** balanced medium-wide group shot  
**Dominant subject:** the complete roster, with a clearly chosen lead operator

### Image description
All three operators appear together and remain large enough to identify. They are not evenly spaced mannequins. Their body lines create a group rhythm: one forward, one slightly offset, one turned toward the river-facing display. Each has negative space around the weapon and silhouette. Their heights, shoulder widths, stances and equipment differ.

The selected operator receives the strongest key light and the clearest focus. The other two remain readable in slightly softer contrast. The environment supports the group with a layered command wall, glass depth and one distant staff silhouette. No central column should slice through a face or weapon. No bright pane should turn the group into low-contrast ghosts.

### Ensemble motion
They should not all breathe, blink, turn or shift at the same frame. Each action has a unique phase and intention. Field Ranger's gaze may settle; Delta Recon finishes a screen check; River Scout completes a river scan. Their motion overlap creates an ensemble, not synchronised idle loops.

A low amount of environmental activity keeps the scene alive: a screen map refreshes, a beacon changes state, a ferry moves beyond glass and a fan rotates. Each motion has its own cadence. Avoid every element pulsing at one frequency.

## 17. Shot B6 — Selection becomes interaction

**Time:** 00:09.2–00:12.0  
**Frames:** 221–288  
**Lens language:** selected-operator close-up to stable UI composition  
**Dominant subject:** selected operator and readable selection controls

### Image description
The camera returns to the selected operator. The character's face and upper body dominate the composition. The background remains recognisably Delta Command but is less sharp and less bright. The selected operator name, role and concise kit information enter in an intentional typography block. It is aligned with the composition and does not cross the face, weapon or important silhouette.

Play/Deploy is visually primary. Other navigation is grouped and subordinate. Selection changes need a designed transition: light emphasis shifts, focus moves, camera reframes, the newly selected operator's performance becomes active, and the text block changes. Do not simply swap a portrait texture.

### UI continuity
The transition from film to interactive lobby must preserve spatial continuity. The film ends on the actual selected roster actor and the live Godot UI should take over that same actor, not spawn a second copy or show an unrelated static picture. Input becomes active at the precise designed hand-off. Touch must interrupt the sequence immediately.

### Rejection conditions
Reject if the three operators are small, if their bodies appear recoloured rather than distinct, if a glass plane or pillar hides them, if the selected character's role is unclear, or if the UI cannot be interacted with after the film.

---

# PART IV — SEQUENCE C: ORIGINAL A-SQUARE NAME REVEAL

## 18. The delta mark as an authored event

The A-Square reveal is a short standalone film beat and can also serve as the bridge between startup and the first login environment. The design should feel like a mark discovered through the language of the world.

Begin with a macro detail: water passing around a weathered stone edge, a narrow painted river line on a surface, or an etched metal channel catching a grazing highlight. The camera travels along the detail. One line forks. A second path meets it. The branching shape gradually resolves into the original delta emblem.

Do not use a generic torus, three spinning triangles, a glowing ring or a default particle explosion. The mark needs a recognisable silhouette, designed negative space, intentional material, clear typographic relationship and strong small-size readability.

## 19. Timing score

### C1 — Anticipation
A near-black but textured frame; a narrow specular line appears at one edge. Ambient low-frequency river tone enters. The light is visible because the material catches it, not because a random emissive object flashes.

### C2 — The path
The camera tracks along a curved river-like channel. The highlight travels with a controlled acceleration and slight easing. A small secondary reflection appears in a second channel. Both paths are not perfectly symmetrical.

### C3 — The mark
The branching river lines meet and reveal the delta silhouette. The mark forms through a combination of shadow, material and light. It should feel physically crafted without pretending to be a literal map.

### C4 — Wordmark
A-SQUARE appears with intentional kerning and spacing. A very subtle reflection or emboss may show its surface. Avoid noisy particle trails and overdone glow.

### C5 — Hold and transition
The emblem settles. The title holds long enough to read. The camera or light then reveals the first environmental detail of Shariatpur. The title does not spin off-screen; it dissolves or transitions through a motivated visual match.

---

# PART V — CHARACTER PERFORMANCE SCOREBOOK

## 20. Field Ranger — grounded frontline readiness

Field Ranger should feel ready without performing constant aggression. The stance is stable; the weapon remains secure. Breathing is visible in the torso and gear, with small delayed movement in straps. His attention is outward, not fixed on the viewer from frame one.

### Performance components
- eye movement begins before the head turn;
- neck rotation follows eyes and leads the torso;
- shoulder alignment compensates for the weapon's weight;
- the support hand maintains a proper grip;
- the trigger hand remains consistent with the selected weapon;
- pelvis and feet maintain contact with the floor;
- gear and sling follow the torso with slight lag;
- a deliberate pause communicates readiness.

### Review questions
Does the gaze have a target? Are hands touching the object? Does the stock sit in the correct place? Does the elbow line make sense? Does the helmet/strap fit? Does the idle have a beginning, middle and held finish rather than continuous noise?

## 21. Delta Recon — attentive precision

Delta Recon's silhouette and acting must be individually designed. Her role is expressed in the way she observes, handles her equipment and settles her stance. Her head/eye timing differs from Field Ranger. Her kit does not merely use a blue-gray colour.

### Performance components
- a brief glance to a screen or distant signal;
- precise eye lead and small head follow;
- a controlled shoulder correction;
- one small deliberate equipment check if the clip supports it;
- a held scan with clean foot contact;
- a soft return to a forward-ready posture.

### Review questions
Is the face and body visibly distinct? Does the pose fit the recon role? Are the proportions preserved in the rig? Does hair/headwear intersect? Is the pistol/weapon grip convincing? Do hands and fingers remain separated and readable?

## 22. River Scout — experienced, weight-bearing observation

River Scout's performance carries experience through stillness and measured action. He does not need exaggerated acting. The difference comes from anatomy, weight distribution, clothing and the timing of a slow scan.

### Performance components
- a stable planted stance with slightly asymmetric support;
- a slow riverward scan;
- torso follows the head in a restrained arc;
- a subtle weight settle after the look;
- facial expression remains attentive and composed;
- heavier gear settles with visible but restrained lag.

### Review questions
Does the older face read at portrait distance? Does body weight feel grounded? Do clothes and equipment have a different silhouette? Does the actor avoid the same timing as the other characters?

## 23. Motion curve craft

Imported animation clips are raw performance material. Never treat the number of clips as quality evidence. The animator must examine source timing, contacts and deformation, then select, trim, retime, blend, layer or manually repair the action.

For a hero motion, inspect at least:
- anticipation frame;
- contact/action frame;
- maximum pose;
- transition/overshoot frame;
- final settle;
- beginning and ending of a repeated loop.

Avoid flat linear motion where a body needs ease. Avoid automatic Bezier smoothing where a hand must hold contact. Use sharp/held curves for deliberate stops; soft curves for weight and breath; overlap for secondary parts. A body is not a single rigid object. Head, chest, pelvis, hands, feet, equipment and hair each have separate timing.

A believable turn is not one Euler rotation. It involves eye lead, head/neck, shoulders, torso, pelvis and foot pivot. A believable stop has deceleration, balance recovery and a small settle. A believable idle is not a constant sine wave applied to every bone.

---

# PART VI — ENVIRONMENT PERFORMANCE AND SURFACE ART

## 24. The river is an actor

Water in Shariatpur is not background decoration. It provides scale, continuity and the strongest opportunity for cinematic reflections. The river has multiple visible systems:

1. broad slow swell;
2. cross-current ripples;
3. fine wind ruffles;
4. shoreline disturbance;
5. boat wake;
6. moving reflected highlights;
7. broken reflections of structures and sky;
8. subtle changes in roughness and colour with viewing angle.

The river material must contain a range of dark and bright values. Deep water may lean blue-green. Sunlit areas can move toward pale warm silver. The waterline is darker and often muddier. Near the ghat, small waves interact with stone edges and mooring objects.

### Water production prompts
**Hero surface prompt:** Create a physically coherent river surface with broad directional swell and several smaller wind-driven ripple scales. Keep the silhouette calm; place bright highlights only where the light direction supports them. Use normal breakup and roughness variation to distort reflection. The result should read as a working river, not a swimming pool, plastic sheet or perfect mirror.

**Reflection prompt:** Reflect the sunlit sky, the strongest building silhouettes, a passing launch and a few shoreline lights. Reflections must bend, stretch and fragment with surface normals. They should not be painted as duplicated architecture below the waterline.

**Wake prompt:** Build a wake that originates at the vessel's stern, widens irregularly, loses energy and dissolves into the surrounding ripple field. Use foam only at plausible shear points. Do not create equal repeated white curves.

**Shoreline prompt:** Create wet/dry bands, darkened joints, edge chips, deposits and broken tiny wavelets. Let water touch the geometry; do not place a perfectly clean hard line between land and river.

## 25. Buildings — ordinary life deserves art direction

The settlement should be built from a family of original, distinct structures rather than one repeated facade. A block may contain a corner shop, a narrow vertical house, a mixed-use building with a deep balcony, an older brick building, a repaired concrete structure and a small workshop. Their shapes, openings, roof life and colour histories are different.

### Architectural detail language
- irregular floor-to-floor heights where the structure demands it;
- recessed window openings with varied depth;
- sills, lintels and sunshades;
- balcony slabs and railings with different patterns;
- painted, weathered signboards and Bengali signage;
- shutters with dents, faded paint and uneven slats;
- awnings with folds, stitching and stretched fabric;
- roof tanks, pipes, dishes, antennas and repairs;
- cable runs that sag between attachment points;
- drainage marks beneath ledges;
- dampness and algae near the waterline;
- dust, soot and rain staining that follow gravity;
- interior light differences visible through selected windows.

### Facade identity prompt
Design each hero building from a clear local-use story. Choose what happens on the ground floor, what occupies the upper floors, how residents access the roof, where the utility cables attach, where rain collects, which wall faces the sun, and what materials have been repaired. Use a different silhouette and opening rhythm for each building. Only after that should signs, textures and micro-detail be added.

## 26. The CNG — a vehicle, not a green toy

The CNG has a recognisable three-wheel layout, front apron, fender, cabin, canopy, posts, windscreen, seat and passenger opening. The canopy shape must feel stretched over a frame. The front wheel and front body are proportionally correct. Headlamps, indicators, mirrors and number plate are separate authored components.

The paint should show different reflectance on the nose, canopy supports and older body panels. Rubber is matte. Chrome or polished metal is limited to selected edges. Hand-contact surfaces show wear. The windscreen reflects the environment but allows enough transmission to read the cabin.

Movement requires:
- wheel rotation based on actual travel distance;
- steering response at the correct wheel;
- a slight suspension settle;
- controlled chassis roll where direction changes;
- stable canopy and passenger-space construction;
- no vertical bob independent of the road;
- screen direction that preserves the hero's visibility.

## 27. The launch — hull, buoyancy and wake

A launch is made from a hull, deck, cabin, glazing, rails, bumpers, rope and working details. It must sit in the water rather than hover above it. The hull's waterline should be consistent. The vessel has subtle yaw and roll; it does not move like a rigid toy sliding on a table.

A passing launch changes the water, reflections and wake. A mooring rope may tighten or relax slightly. Reflections move with the boat. The boat's speed, wake length and camera motion must agree. The launch is not a decorative background object; it is an environmental performance.

## 28. Trees and foliage — authored natural forms

A tree should have an identifiable trunk, branching structure, canopy mass, leaf direction, silhouette breakup and relationship with light. Avoid a cluster of repeated spherical leaves. Use a designed canopy silhouette and several leaf sizes, colours and densities.

Branch and leaf motion is low amplitude and asynchronous. The whole tree should not sway like a single rigid object. Outer branches respond slightly more than thick inner limbs. Leaf groups have delayed and varied motion. A single gust can travel through the canopy rather than every leaf moving at once.

## 29. Atmospheric layers

Distance is built from contrast, saturation, edge clarity and light, not just fog. Near objects retain rich texture and contact shadows. Middle-distance buildings lose some contrast but keep their silhouette. Far-bank structures have softer edges and cooler values. The sky, river and land share a single atmospheric direction.

Use haze with restraint. The camera may see a slight veil over the far bank or one streak of warm sun, but fog should never hide the subject. Volumetric light is a compositional accent; it must have a source and a path.

---

# PART VII — LIGHTING, SHADING AND COLOR

## 30. Login film lighting recipe

The Shariatpur film uses a warm, late-afternoon key and cooler sky/river fill. The sun angle should describe the geometry: shop awnings cast shadow; roof tanks and antennas catch an edge; tree leaves create broken shade on asphalt; the launch cabin has one bright side and one softer shaded side.

Use:
- one dominant warm key;
- one broad cool fill with enough exposure to keep shadows readable;
- a narrow rim for the operator, CNG and launch where motivated;
- practical lights only where fixtures exist;
- local bounce from warm wall surfaces;
- restrained water glints and reflection highlights.

Do not light every object equally. Faces, hero vehicles and key architectural silhouettes are prioritised. Background props may remain darker and less saturated.

## 31. Lobby film lighting recipe

The lobby combines cooler river fill through glazing with warm task lights around consoles and operator faces. A selected operator receives a directional key and controlled rim. The two secondary operators remain distinct but do not compete for the same exact brightness.

Glass should have visible reflectance without becoming an opaque cyan wall. The viewer should still see the operators and the far environment. Avoid a large overexposed glass plane between camera and characters. If the glass is part of the architectural identity, frame it as an edge or background element, not an obstructing foreground layer.

Metallic materials should show reflected light but keep roughness variation. Dark floor surfaces may show soft, broken reflections of shoes, podiums or console lights. Do not cover the floor in a perfect mirror. Warm tungsten light should have a local pool, not wash the entire room.

## 32. Material art direction by surface

### Skin
Use layered colour variation, controlled subsurface response, realistic roughness, restrained specular and a detailed eye. Skin should not have the same roughness everywhere. The nose, forehead, cheek, lips and under-eye areas respond differently. Avoid wax, rubber or plastic.

### Hair and headwear
Hair should have volume, direction and breakup. Strands or clusters need highlight variation. Helmet edges should not clip the scalp or eyebrows. Straps need thickness and contact. Hair/headwear must be reviewed from front, side and three-quarter angles.

### Fabric
Show weave scale, compression folds, seams, stitching, reinforcement panels and wear. The fabric has a different highlight than polished metal. Folds should occur at joints, contact points and tension lines, not as random noise.

### Webbing and gear
MOLLE rows, pouches, buckles, straps and radio elements should be coherent in scale and placement. Each pouch needs a closing flap or seam. Straps route around the body and do not disappear through it. Metal buckles have limited bright edges.

### Concrete and brick
Surface scale must match the building. Large stains follow gravity; chipped edges occur at contact points; patch repairs interrupt the base material. Use subtle displacement/normal details rather than noisy high-frequency mottling across everything.

### Glass
Reflections and transmission are balanced. In a strong lobby composition, a viewer can see both the room and the river, but operators are still the clearest subjects. Glass thickness, mullions and edge reflections help it feel architectural.

### Water
Use colour variation, normal layers, roughness breakup, view-angle response and reflection distortion. The strongest highlights should move with the camera, waves and objects. The surface must not become one uniform turquoise shader.

## 33. Color grade

### Login grade
Warm highlights, river-teal shadows, natural skin, muted brick, deep foliage and charcoal asphalt. Preserve local colour. Avoid pushing the whole image toward orange/teal until every object loses identity.

### Lobby grade
Graphite and teal architecture, warmer faces and task lighting, controlled amber and red accents, dark but readable materials. Avoid oversaturated cyan emissive surfaces. A selected operator should have a clear separation from the room.

### Technical review
Use a repeatable base transform. Compare neutral material swatches under the final key, fill and rim setup. A LUT is only adopted after license and runtime compatibility review. Save the grade settings in the scene and manifest.

---

# PART VIII — CAMERA AND EDITING GRAMMAR

## 34. Shot grammar

The edit uses wide, medium and close shots for different reasons:
- wide: geography and scale;
- medium: action and relationship;
- close: identity, face, gear and emotion;
- detail: material, hand contact, water interaction and a designed reveal.

Do not use a wide shot to show everything. Do not use a close-up when the viewer needs to understand the environment. Do not keep the camera moving through a moment that should be held. A pause can carry more emotion than another camera move.

## 35. Camera movement

Each move needs an object or story reason. A lateral truck reveals parallax. A dolly approaches a subject. A pan follows motion. A tilt discovers scale. A focus pull transfers attention. An orbit reveals form. Camera shake is an accent, not the default state.

The camera should not repeatedly cross its own subject or lose the operator's face. Motion curves have anticipation, acceleration, ease, braking and a settle. A camera move can be impossible in reality if that produces a better piece of game art, but it must remain intentional and smooth.

## 36. Focus and lens

Depth of field is a storytelling tool. Keep the eyes in focus during a portrait. Do not blur a whole environment merely to appear cinematic. Wide lenses reveal space but can distort people and architecture. Longer lenses compress distance and can make a portrait feel intimate. Lens choice must be motivated by the subject and spatial story.

A rack focus should have a clear start and endpoint. Focus does not randomly hunt. Exposure and focus changes should not cause visible flicker or pump unless a designed camera event requires it.

## 37. Transitions

Transitions are not all fades. Use visual matches:
- a river reflection becomes a curved emblem line;
- a bright shop sign becomes a lobby display light;
- a boat cabin window becomes a command-room glass bay;
- the operator's gaze directs the eye to a mode card;
- a title line resolves into a real progress line.

A transition must preserve orientation and brand identity. Keep important interface text out of fast-moving regions. The user should always know what is happening and what they can tap.

## 38. Animation curves and frame reviews

Use a deliberate curve shape for each event. A slow camera move may begin almost imperceptibly, accelerate through the middle and ease out into a held frame. A title may accelerate quickly and settle softly. A head turn may have a short eye lead, a slightly slower head/neck response and a torso follow. A strap moves after the torso, not before it.

Review frames at the beginning, quarter, middle, three-quarter and end of each sequence. Also review the fastest camera movement, the operator's strongest pose, the tightest hand/weapon contact and the largest reflection. A sequence is not approved because its frame 144 looks good.

---

# PART IX — LOADING, UI AND MODE-FAMILY ART

## 39. Loading is a designed pause, not a fake animation

A loading scene should be beautiful without lying. The progress indicator reflects actual download, extraction, verification, decompression or activation state. The background may show a district image, one gentle camera move, subtle river or foliage motion and a route line. Never animate the progress bar faster than real work or show a completed value before the process is complete.

For Shariatpur, a loading composition could show the river bend, a boat route and the district name. A small weather/time label is shown only if data are actually available. The UI must clearly distinguish downloading, verifying, preparing assets and ready-to-enter states.

## 40. Mode family visual identity

A-Square must not display several cards that are just renamed versions of Battle Royale.

### JibonJatra
A lived-world identity. The artwork is warm, open, local and story-driven: a road, a neighbourhood, a market, a vehicle or a human interaction. Its sub-activities may include Roadline and Pitchbound. They remain under one coherent world-life family, not separate top-level modes.

### Strikefront
A tactical combat identity. The art can use hard directional lighting, strong silhouettes, character/weapon close-ups, and a precise squad/solo presentation. Last Stand remains clearly solo. Strike Front presents its intended solo and squad entry paths without duplicating a second Battle Royale card.

### Greenwake
An exploration/adventure identity. Use landscape scale, water, ports, ruins, pathways and environmental storytelling. It should feel distinct from the tactical combat family and from everyday neighbourhood activity.

### Mode-card rules
Each card has one memorable composition, one clear action, one concise description and a real destination. Unsupported online services remain visibly unavailable rather than pretending to matchmake. Loading state and selection are truthful. The title and card typography must remain readable on mobile.

---

# PART X — BLENDER AUTHORING AND EXPORT SCORE

## 41. The master asset principle

Author the highest-quality original source that can be created and preserved. Do not begin by sacrificing the sculpt to hit an unmeasured mobile budget. Keep the master mesh, texture source, rig and source license separate from the runtime LOD export.

The source package should preserve:
- editable Blender scene and linked assets;
- original/high master meshes and retopology;
- UV sets and bake outputs;
- PBR textures with source/license references;
- rig, skin weights and animation actions;
- shape keys/morphs;
- cameras, lights, markers and shot metadata;
- render configuration and colour-management settings;
- asset manifest and source hashes;
- preview renders and review films.

## 42. Character rig preparation

Before importing a roster model into a shot:
1. check the actual skeleton and bone naming;
2. inspect the neutral pose and body proportions;
3. review the animation library and choose clips based on acting intent;
4. check hand/weapon and foot contacts;
5. verify skin deformation at shoulder, elbow, hip, knee and wrist;
6. review face shapes and eye/head movement;
7. identify clothing/gear meshes that require secondary motion;
8. create camera-specific performance edits;
9. export and re-import the result for visual confirmation.

## 43. Static and skinned mesh handling

Skinned meshes and shape-key meshes must never be merged into static geometry. Static environment meshes may be consolidated after checking material slots, UVs, normals and object origins. Keep the high-detail scene organised into collections with stable names. Preserve the actor rigs through every triangulation, batching and export stage.

## 44. River and reflection export

The offline river may use a dense tessellated mesh, multiple animated shape keys, layered shaders, animated normals and screen-traced reflections. The Android export must be separately profiled. Screen-space reflection is not assumed to be available or performant on every mobile device. The game runtime can use a cheaper representation with baked reflection probes, reflection textures, simple wave displacement or shader-only ripple detail. The offline master is not to be stripped just because the phone runtime requires measured simplification.

## 45. Camera and film export

Export film and environment as separate deliverables. The film render keeps the temporary operator rigs visible. The environment GLB removes preview-only actors only after the film and still renders are complete. If a camera action is baked from an authoring extension, the final GLB must not require that extension at runtime.

Each shot should carry named cameras, lens metadata, focus points, markers and a documented frame range. The MP4 must have even dimensions for H.264 YUV420. Render one still image at a key frame and frame samples across the whole sequence.

## 46. LOD and mobile delivery

Maintain a high-detail master and derive medium/low variants only after the source is artistically approved. LODs must preserve silhouette, face shape, hand/weapon contact, gear layout and animation deformation. Use normal/AO/roughness bakes to retain source detail. Texture compression, atlas layout, streaming, visibility, texture resolution and memory budgets are measured on the actual target device.

A 4K, 8K or denser source texture may be appropriate to the master. The shipped mobile texture can be smaller if it still preserves the look at the device's viewing distance. Never confuse offline art quality with APK size.

---

# PART XI — ART-REVIEW GATES

## 47. Review pass 1: composition
- Can the primary subject be identified in one second?
- Are the foreground, middle distance and far distance doing different jobs?
- Is the operator large enough?
- Does the camera reveal rather than merely move?
- Are major shapes separated and balanced?
- Is negative space protected around the face, weapon and title?

## 48. Review pass 2: modelling
- Do hero silhouettes read without texture?
- Are objects coherent rather than piles of boxes/cylinders?
- Are there distinct facade profiles and operator identities?
- Are construction details at a believable scale?
- Does the object survive a turntable review?

## 49. Review pass 3: materials and lighting
- Are skin, fabric, webbing, metal, concrete, glass, rubber, foliage and water visibly different?
- Do roughness and normal maps have the right scale?
- Are highlights motivated by light sources?
- Are shadows preserving form?
- Are reflected shapes visible without turning every surface into a mirror?
- Is the grade protecting skin and local identity?

## 50. Review pass 4: animation
- Does every motion have an intention?
- Are timing and overlap individual to each actor?
- Are contacts correct?
- Does secondary motion follow the primary action?
- Are loops free of pops?
- Does the camera preserve the subject?
- Do water, wake, traffic, leaves and lights have different timing?

## 51. Review pass 5: mobile readability
- Does the scene read at actual phone resolution?
- Are title and UI text clear?
- Can the selected operator be identified?
- Are important controls still tappable?
- Does the image retain contrast with screen brightness reduced?
- Are loading and mode states honest?

## 52. Approval states

Every deliverable must use one of these labels:

- **SOURCE READY:** editable source files and required metadata exist.
- **STRUCTURAL PASS:** scripted validation has passed.
- **RENDER PASS:** the actual still and film files were produced.
- **VISUAL REVIEW PASS:** a human reviewer has inspected the images/frames and approved composition, art, timing and subject readability.
- **GODOT IMPORT PASS:** the exported assets load and play in the pinned engine.
- **ANDROID DEVICE PASS:** the result has been tested on the target class of phone for memory, frame pacing, heat, touch, loading and crash behaviour.
- **INTEGRATED:** all required gates have passed and the approved revision is used by the canonical project.

No lower gate implies any higher gate.

---

# PART XII — PRODUCTION PROMPT LIBRARY

These prompts are authored as direction for the Blender artist/technical artist. They are not a request to generate a generic concept image and call it final. Each prompt should result in editable scene work, source files, material data, animation curves, cameras and review output.

## Prompt 1 — Shariatpur river master
Create an original, deeply detailed Shariatpur-inspired riverfront scene. Compose the river as a living subject with a readable horizon, a near ghat, a local road, distinct everyday buildings, roof life, trees and a launch. Build the hero river from layered surface forms, fine wave detail, irregular reflections and shoreline transitions. Every reflection must be distorted by the water and related to the environment. Use warm late-afternoon light and cool river fill. The final image must have depth, human scale, a memorable silhouette and an emotional point of view. Do not use repeated box facades, perfect mirrored water or generic futuristic decoration.

## Prompt 2 — Local street architecture
Create a family of individual Bangladeshi mixed-use buildings. First design their silhouettes, floor rhythms, balconies, openings, roof additions, shop access, awnings and service lines. Then add material age, signboards, shutters, wiring, rain staining, drainage marks and interior glimpses. The buildings should look like they were designed, repaired and inhabited over time. Give every hero facade a different construction story and a distinct shadow pattern. Avoid a stamped modular wallpaper look.

## Prompt 3 — CNG hero vehicle
Sculpt and model a recognisable local three-wheeler with coherent canopy, front apron, windscreen, passenger opening, seats, fenders, wheels, lamps, mirrors and plate. Treat metal, glass, rubber, painted panels and canvas separately. Add restrained wear and contact polish. Animate travel with correct wheel rotation, steering, chassis response and suspension settle. Keep the vehicle in a clear lane and preserve the operator's silhouette.

## Prompt 4 — Launch and water interaction
Create a small local launch with a coherent hull, deck, cabin, glass, rail, bumpers and rope details. Animate a gentle glide, low buoyant bob and slight yaw. Build an irregular stern wake that spreads and breaks down into the wave field. The reflected hull and cabin should fragment and move. The launch should feel heavy and connected to the water.

## Prompt 5 — Field Ranger portrait
Using the actual Field Ranger rig, create a three-quarter cinematic portrait. Begin with gaze away from the lens, let the eyes lead a measured head turn, then allow shoulders and torso to settle. Preserve weapon grip, stock contact, foot support and gear clearance. Layer soft warm key, cool fill and a restrained rim. Skin, eyes, hair/headwear, cloth, vest, buckles, weapon and straps must have separate material response. Hold the final gaze. Avoid a generic whole-body turn or constant procedural bob.

## Prompt 6 — Delta Recon portrait
Using the actual Delta Recon rig, create a performance that differs in both silhouette and timing from Field Ranger. Her attention checks a screen or distant signal. Eyes lead; head and neck follow; the torso makes a small compensating adjustment. Keep weapon hand contact, body shape, hair/headwear and equipment clear. Use a new camera angle and lighting pattern, not just a different costume colour.

## Prompt 7 — River Scout portrait
Using the actual River Scout rig, create an experienced, weight-bearing river-country scout. His older face, facial hair, body proportions, kit arrangement and stance must read distinctly. Let him complete a slow scan toward the river and settle. The heavier body and gear respond with a measured follow-through. Avoid exaggeration; the performance is carried by intention, timing and posture.

## Prompt 8 — Delta Command hall
Create an authored command hall with structural rhythm, believable roof trusses, glass with proper mullions, cable trays, equipment bays, consoles, floor transitions and a view toward the river. Compose it around three hero operator positions, with a camera path that does not look through a washed-out pane or central pillar. The architecture supports the roster. It must not become the subject at the expense of the people.

## Prompt 9 — Three-character group composition
Stage Field Ranger, Delta Recon and River Scout as three separate people. Give each character a distinct stance, line of action, face, kit, equipment weight, animation timing and lighting. The selected operator receives the strongest focus. All three remain recognisable at phone size. Their performance rhythms overlap naturally; do not synchronise the three idle clips.

## Prompt 10 — Original title reveal
Design the A-Square delta mark as a crafted, original symbol. Reveal it through river-like paths and a travelling highlight, then resolve the wordmark and hold. Use a deliberate anticipation, reveal, overshoot and settle. The mark must be legible at small size and should feel connected to the environment. Do not create a spinning generic emblem.

## Prompt 11 — Cinematic grade
Apply a cohesive warm/cool grade with natural skin, rich but controlled foliage, distinct brick/plaster/concrete, charcoal road and river teal. Preserve shadow detail and local material colour. Use contrast to guide attention, not to crush the image. Do not globally raise exposure until every surface becomes pale grey.

## Prompt 12 — Final visual review
Render the opening, quarter, middle, three-quarter and final frames plus the complete film. Review the actual MP4 and the standalone still. Check operator scale, silhouette, face readability, reflections, camera motion, material separation, local identity, contact and transitions. Write down every flaw visible at phone size. Do not mark art approval from a successful compile or GLB verifier.


## Prompt 13 — Shariatpur hero corner store, bespoke environment asset
Create one original Shariatpur riverside corner shop as an authored hero asset, not a repeated building module. Start with a hand-drawn side elevation and a custom roof silhouette. Give it irregular upper parapet heights, a real ground-floor shop aperture, a recessed arched opening, separate glazing panes, deep stone reveals, a side entrance with a handmade timber door and a curved upper balcony. The front elevation should contain true negative space: the shelves and shop interior must sit behind the opening, not on top of a solid wall. Build each façade pier, lintel and sill to tell a construction story. Give the balcony a curved plan, a cast-stone deck, individually bent spindles, brass handrail and a small cast-metal flourish.

The shop must feel lived in. Model shelves at believable reach height, tea jars, rice sacks, a service counter, timber posts, a worn threshold, uneven floor surfaces and a warm practical interior light. The signboard is individually designed and attached to a proper fascia with a hand-painted border. The awning is a cloth surface with visible fold direction, stretched seam lines, a soft irregular front hem, faded canvas panels and a very low-amplitude wind response. It must not behave like a rigid plank. The roof has a ribbed water tank, collar, feed pipe, telephone/electrical cable, parapet repairs and a few utility attachments. Surface wear is placed by gravity, touch, water and sun direction: rain streaks below balcony edges, chipped corners, polished hand-contact areas, dampness around the base and faded sign paint.

Author in custom mesh profiles, sculpted/extruded sections, curved tubes, lathed profiles, cloth grids, UVs and properly assigned PBR materials. Do not construct the hero façade from a stack of cubes or decorate a solid box with pasted rectangles. Review the silhouette in black, the material response in neutral light, the interior from the street camera and the final sunset shot. The camera should recognise it as a real corner shop in one second.

## Prompt 14 — Bangladesh CNG, hero vehicle asset and road performance
Create a recognisable local three-wheel CNG as a complete vehicle, not a green toy shell. Start with a three-wheel stance and a hand-designed side silhouette: sloped bonnet, front apron, passenger tub, open doorway, bench, driver cowl, footwell and a curved roof canopy. Separate every major material and component. The body is stamped/formed metal with slightly different curvature on nose, side panel and rear tub; the canopy is faded fabric over a thin tubular frame; the windscreen is laminated glass with thickness and reflections; the trim is aluminium or painted metal; the tyres are matte rubber with individual tread blocks; the hub/rim is machined metal with visible spokes and a central cap.

Make the cabin readable through the side opening. Show the bench cushion, backrest, stitched seams, grab rails, inner trim, dashboard, handlebar and driver controls. The canopy should have transverse bows, curved pillars, seams, a scalloped edge and a cloth response to a breeze. Use a separate shape key or layered animation track for the roof fabric. Do not sway the whole canopy as one rigid panel.

The front wheel is the single steering wheel; the rear axle has two wheels. Each wheel has a distinct pivot, tyre mesh, tread, sidewall, rim, spokes and hub cap. Wheel rotation should correspond to the total distance travelled, not an arbitrary looping spin. The front wheel changes steering direction at turn-in. The chassis settles under acceleration and braking, rolls slightly during a turn, and responds to road imperfections through restrained suspension movement. The passenger body should have a slight weight response, while the canopy fabric and loose trim lag differently. Headlights, indicators, mirrors, number plate, enamel pinstripe, mudguard and side registration badge are individual authored components.

For the hero pass, set a clear screen direction and a precise camera mark. The CNG should approach with a readable silhouette, decelerate slightly near the camera, cross the frame, then leave the shot without hiding the operator. Track its wheels against the road; do not let them slip through the surface or float. Use a low three-quarter lens to see body depth and passenger opening, then a close detail insert for the wheel, canopy and enamel badge. The final still must read as a real working three-wheeler at phone size.

## Prompt 15 — Launch hull, buoyancy, wake and water reflection performance
Build a small local passenger launch with a coherent hull rather than a rectangular boat body. Sculpt the bow rise, stern transition, keel line, rubbing strakes, waterline, deck, cabin walls, window frames, roof edge, railings, doors, bumpers, ropes and fenders. Use a distinct hull material and layered paint wear. The cabin windows need real frame depth and reflections. A few practical details—mooring cleat, rope coil, small light, worn step, rubber fender and painted lettering—establish use.

Animate low-frequency buoyancy, small roll and yaw, and a subtle current response. The launch should feel heavy and supported by the water. Build a wake from the stern, with near-field turbulence, a broad V-shaped spread, small foam at plausible shear points and an irregular fade into the existing wave field. The reflected hull and cabin must stretch and fragment with the wave normals. The river should not show an exact, static mirror copy. Camera motion should keep the launch readable while allowing the far bank to move slowly in parallax.

## 27 November 2026 — bespoke storefront and CNG authoring

The isolated \`art/crafted-riverside-architecture\` and \`art/crafted-cng-vehicle\` branches are separate from the canonical game branch and from one another's active render jobs. The storefront pass replaces one repetitive central mixed-use facade with a custom hero corner store: an irregular roofline, true ground-floor aperture, visible shelves and goods, arched window treatment, custom timber door, curved balcony, forged rails, sculpted cloth awning, roof tank, feed pipe, rain streaks and weathered trim.

The CNG pass replaces the previous helper-built vehicle at the login call site with a bespoke three-wheeler: custom side-profile shell, sloped bonnet, open passenger cabin, shaped floor and seats, laminated windscreen, curved canopy frame, a 26 × 12 cloth roof grid with a keyed gust, three custom toroidal tyre meshes, 44 tread blocks per wheel, separate pivots, hubs/spokes, front-wheel steering and a restrained body suspension performance. The visible-side registration badge is oriented toward the login film camera.

These source details are not visual approval. The latest Blender run must compile, build the scene, render the still and 12-second review film, export the GLB and survive the scene verifier. The PNG and MP4 must then be inspected at phone scale. No integration or claim of film-grade completion is implied until those gates pass.

---

# PART XIII — CURRENT REVISION RECORD

## 27 November 2026 — river authoring and cinematic render corrections

The isolated branch \`feature/three-distinct-ara-operators\` gained a tessellated river master with four authored shape-key phases, layered water PBR detail, EEVEE screen-traced reflection setup and source-level regression tests. The river section's local mesh is explicitly offset to its intended river position.

The film encoder previously failed because the review frame height was odd (1200 × 675). The dedicated editorial preview now uses 50 percent of the 1600 × 900 scene (800 × 450) and 16 EEVEE render samples when supported. This is only the blocking/acting/composition review pass; the still review returns to 75 percent and the approved final film uses a separate full-quality profile.

The corrected run still has to produce the actual login and lobby renders. Water build logs and rig-preservation checks are evidence of construction, not proof of visual quality. The current scene composition and the older previews remain subject to art-direction review and substantial improvement. No art approval, Godot import approval, Android device approval or canonical integration is implied here.

## Revision rule

When a change improves a render, record the exact commit and show the corresponding frame/film. When a change makes a scene worse, revert it or redesign the shot. Do not hide a failed visual review behind a higher triangle count, a longer description, more objects or a green structural test.

The final A-Square experience must feel like a set of premium, directed game worlds joined into one original Bangladesh-rooted universe. Its quality comes from design, performance, light, material, composition, sound, pacing and care—not from the number of primitives in a Blender outliner.
