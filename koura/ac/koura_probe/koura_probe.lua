-- Adapted from mapcreator's mc_probe by Forcky and contributors, Apache-2.0.
-- Source: https://github.com/Forcky/mapcreator/tree/efe4a7cf9961fc36b2d4fa1739e4c7fb349aa378/harness/csp_app/mc_probe
-- Changes: reads Koura probe points and omits AI spline measurements for free roam.
-- The upstream teleport-and-check approach follows stormbuster/assetto-corsa-mcp.

local dir = ac.getFolder(ac.FolderID.ACDocuments) .. '/koura_probe'
-- Wait this long in sim time after each teleport: the car drops ~0.5 m and must settle before it's read.
local SETTLE_S = 1.2
-- ac.makeScreenshot captures a later frame, not this one: before M3's fix (issue #14) each shot showed the
-- next point and the last one was lost to the quit. So keep the car where it is this long after a shot.
local SHOT_HOLD_S = 0.5

local state = 'loading'
local points, results, index, wait, hold = nil, {}, 1, nil, nil
local options = { quit = false, screenshots_every = 0 }
local camera

local function save(name, value)
  io.save(dir .. '/' .. name, JSON.stringify(value))
end

local function vec(t)
  return vec3(t[1], t[2], t[3])
end

local function set_camera(view)
  if view == nil then
    if camera then camera:dispose() end
    camera = nil
    return
  end
  camera = camera or ac.grabCamera('Koura terrain probe')
  if camera == nil then return end
  local pos = vec(view.pos)
  camera.transform.position:set(pos)
  camera.transform.look:set((vec(view.target) - pos):normalize())
  camera.transform.up:set(0, 1, 0)
  camera.fov = view.fov or 52
end

local function load_points()
  local raw = io.load(dir .. '/points.json')
  if not raw then return false end
  local data = JSON.parse(raw)
  points = data.points
  options.quit = data.quit or false
  options.screenshots_every = data.screenshots_every or 0
  options.utc_timestamp = data.utc_timestamp
  return points ~= nil and #points > 0
end

local function record(p)
  local car = ac.getCar(0)
  local wheels = {}
  for w = 0, 3 do
    local wheel = car.wheels[w]
    wheels[#wheels + 1] = {
      contact = { wheel.contactPoint.x, wheel.contactPoint.y, wheel.contactPoint.z },
      valid_track = wheel.surfaceValidTrack,
      surface = wheel.surfaceSectionIndex,
    }
  end
  local above = car.position + vec3(0, 20, 0)
  local hit = physics.raycastTrack(above, vec3(0, -1, 0), 60)
  local sim = ac.getSim()
  local view_pos = sim.cameraPosition
  local terrain_rays = {}
  for _, ray in ipairs(p.terrain_rays or {}) do
    local origin = vec(ray.pos)
    local distance = physics.raycastTrack(origin, vec3(0, -1, 0), 60)
    terrain_rays[#terrain_rays + 1] = {
      name = ray.name,
      camera_distance_m = (origin - view_pos):length(),
      expected_distance_m = ray.expected_distance_m,
      distance_m = distance,
    }
  end
  -- Frame rate at this point, as CSP reports it; a missing field on the sim struct would throw, hence pcall.
  local ok, fps = pcall(function() return sim.fps end)
  results[#results + 1] = {
    fps = ok and fps or nil,
    local_time = { hour = sim.timeHours, minute = sim.timeMinutes },
    i = index,
    requested = p.pos,
    position = { car.position.x, car.position.y, car.position.z },
    wheels = wheels,
    wheels_outside = car.wheelsOutside,
    raycast_m = hit,
    camera_position = { view_pos.x, view_pos.y, view_pos.z },
    camera_owned = camera ~= nil and camera:active(),
    terrain_rays = terrain_rays,
  }
end

local function finish()
  state = 'done'
  set_camera(nil)
  save('results.json', { results = results, csp = ac.getPatchVersionCode() })
  save('status.json', { state = state, points = #points })
  -- os.remove is a stub inside CSP's sandbox; io.deleteFile is the real one. Without this the
  -- probe would run again (and teleport the car) on every later launch.
  io.deleteFile(dir .. '/points.json')
  if options.quit then ac.shutdownAssettoCorsa() end
end

function script.update(dt)
  if state == 'loading' then
    if load_points() then
      state = 'starting'
      save('status.json', { state = state, points = #points, csp = ac.getPatchVersionCode() })
    end
  elseif state == 'starting' then
    -- CSP's own start button keys on isInMainMenu (the pits setup screen); this works on 0.2.11.
    local sim = ac.getSim()
    if sim.isInMainMenu then
      ac.tryToStart(true)
    else
      if options.utc_timestamp then
        ac.setWeatherExactUTC0Timestamp(options.utc_timestamp)
        ac.setWeatherTimeMultiplier(0)
      end
      state = 'probing'
    end
  elseif state == 'probing' then
    if hold ~= nil then
      hold = hold - dt
      if hold > 0 then return end
      hold = nil
      if index > #points then finish() end
      return
    end
    if wait == nil then
      local p = points[index]
      -- CSP 0.2.11 faces the car *against* the direction it's given (M3, issue #14), so pass the
      -- reverse of the road's forward vector to face along the road.
      physics.setCarPosition(0, vec(p.pos), vec({ -p.dir[1], -p.dir[2], -p.dir[3] }))
      set_camera(p.camera)
      wait = SETTLE_S
    else
      wait = wait - dt
      if wait <= 0 then
        wait = nil
        record(points[index])
        if options.screenshots_every > 0 and (index - 1) % options.screenshots_every == 0 then
          ac.makeScreenshot(dir .. '/shot_' .. index .. '.png', ac.ScreenshotFormat.PNG)
          hold = SHOT_HOLD_S
        end
        index = index + 1
        if index > #points and hold == nil then finish() end
      end
    end
  end
end

function script.windowMain(dt)
  ui.text('Koura probe: ' .. state)
  if points then ui.text(string.format('point %d of %d', math.min(index, #points), #points)) end
end
