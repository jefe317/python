// Helper function to get calendars
function getCalendars() {
  const myCalendar = CalendarApp.getDefaultCalendar();
  const workCalendarId = "email@gmail.com"; // change this email address to yours
  const workCalendar = CalendarApp.getCalendarById(workCalendarId);
  return { myCalendar, workCalendar };
}

function scheduleWellnessEventsSmart() {
  const dryRun = true; // set to false to actually create events
  const scheduleGetFit = true; // set to false to skip "Get Fit" events
  const scheduleWristStretch = true; // set to false to skip "Wrist stretch" events
  const scheduleLegStretch = true; // set to false to skip "Leg stretch" events
  
  const { myCalendar, workCalendar } = getCalendars();

  const numDaysAhead = 5;
  const now = new Date();
  const seriesId = "wellness-series-" + now.toISOString().split("T")[0];

  for (let offset = 0; offset < numDaysAhead; offset++) {
    const day = new Date(now.getFullYear(), now.getMonth(), now.getDate() + offset);
    const weekday = day.getDay();

    Logger.log(`\n======================`);
    Logger.log(`📅 Checking ${day.toDateString()}`);
    
    // Schedule leg stretches for ALL days (including weekends)
    if (scheduleLegStretch) {
      scheduleLegStretchEvents(day, myCalendar, seriesId, dryRun);
    }
    
    // Skip weekday-only events on weekends
    if (weekday === 0 || weekday === 6) {
      Logger.log(`⏭️ Skipping weekday wellness events (weekend)`);
      continue;
    }

    scheduleDayEvents(day, myCalendar, workCalendar, seriesId, dryRun, scheduleGetFit, scheduleWristStretch);
  }

  Logger.log(`\n✨ Done! DryRun = ${dryRun}`);
}


function scheduleDayEvents(date, myCal, workCal, seriesId, dryRun, scheduleGetFit, scheduleWristStretch) {
  const startHour = 8;
  const endHour = 16;
  const dayStr = date.toDateString();

  // ---- STEP 1: Check if wellness events already exist ----
  const existingWellness = myCal
    .getEventsForDay(date)
    .filter(e => e.getTitle().includes("[Wellness]") && !e.getTitle().includes("Leg stretch"));

  if (existingWellness.length > 0) {
    Logger.log(`🚫 Skipping ${dayStr} — already has ${existingWellness.length} wellness events.`);
    existingWellness.forEach(e =>
      Logger.log(`   • ${e.getTitle()} (${fmt(e.getStartTime())} → ${fmt(e.getEndTime())})`)
    );
    return; // Skip the rest of the logic for this day
  }

  // ---- STEP 2: Collect all events for that day ----
  const allEvents = [
    ...myCal.getEventsForDay(date),
    ...(workCal ? workCal.getEventsForDay(date) : []),
  ];

  Logger.log(`🕑 Found ${allEvents.length} total events for ${dayStr}`);

  // Filter out all-day events (those that start/end at midnight)
  const busySlots = allEvents
    .filter(e => !isAllDay(e))
    .filter(e => e.getTitle() !== "Block")
    .map(e => ({ start: e.getStartTime(), end: e.getEndTime(), title: e.getTitle() }))
    .sort((a, b) => a.start - b.start);

  const ignoredAllDay = allEvents.filter(e => isAllDay(e));
  if (ignoredAllDay.length > 0) {
    Logger.log(`🛑 Ignored ${ignoredAllDay.length} all-day events:`);
    ignoredAllDay.forEach(e => Logger.log(`   • ${e.getTitle()}`));
  }

  Logger.log(`📚 Busy slots (${busySlots.length}):`);
  busySlots.forEach(b => Logger.log(`   - ${b.title} ${fmt(b.start)} → ${fmt(b.end)}`));

  // Compute free gaps
  const dayStart = new Date(date.getFullYear(), date.getMonth(), date.getDate(), startHour, 0);
  const dayEnd = new Date(date.getFullYear(), date.getMonth(), date.getDate(), endHour, 0);
  const freeGaps = [];
  let cursor = dayStart;

  for (const b of busySlots) {
    if (b.start > cursor) freeGaps.push({ start: new Date(cursor), end: new Date(b.start) });
    if (b.end > cursor) cursor = b.end;
  }
  if (cursor < dayEnd) freeGaps.push({ start: new Date(cursor), end: dayEnd });

  Logger.log(`🟩 Free gaps (${freeGaps.length}) for ${dayStr}:`);
  freeGaps.forEach(g =>
    Logger.log(`   gap: ${fmt(g.start)} → ${fmt(g.end)} (${mins(g)} min)`)
  );

  // Helper: log or create events
  function createPairedEvents(title, start, durationMins) {
    const end = new Date(start.getTime() + durationMins * 60000);
    const fullTitle = `[Wellness] ${title}`;
    const desc = `Auto-created wellness event (${seriesId})`;
    if (dryRun) {
      Logger.log(`💡 Would create "${fullTitle}" ${fmt(start)} → ${fmt(end)}`);
    } else {
      const event = myCal.createEvent(fullTitle, start, end, {
        description: desc,
        reminders: { useDefault: false, overrides: [] },
      });

      if (workCal) {
        workCal.createEvent("Block", start, end, {
          description: `Auto-blocked for personal wellness (${seriesId})`,
        reminders: { useDefault: false, overrides: [] },
        });
      }
      Logger.log(`✅ Created "${fullTitle}" ${fmt(start)} → ${fmt(end)}`);
    }
  }

  // --- Schedule Get Fit (15 min) ---
  let fitGap = null;
  if (scheduleGetFit) {
    fitGap = freeGaps.find(g => g.end - g.start >= 15 * 60000);
    if (fitGap) {
      Logger.log(`🏋️ Using gap ${fmt(fitGap.start)} → ${fmt(fitGap.end)} for "Get Fit"`);
      createPairedEvents("Get Fit", fitGap.start, 15);
    } else {
      Logger.log(`⚠️ No room for "Get Fit" on ${dayStr}`);
    }
  } else {
    Logger.log(`⭐️ Skipping "Get Fit" (disabled)`);
  }

  // --- Rebuild gaps after "Get Fit" ---
  const newBusy = [
    ...busySlots,
    ...(fitGap ? [{ start: fitGap.start, end: new Date(fitGap.start.getTime() + 15 * 60000) }] : []),
  ].sort((a, b) => a.start - b.start);

  const updatedGaps = [];
  cursor = dayStart;
  for (const b of newBusy) {
    if (b.start > cursor) updatedGaps.push({ start: new Date(cursor), end: new Date(b.start) });
    if (b.end > cursor) cursor = b.end;
  }
  if (cursor < dayEnd) updatedGaps.push({ start: new Date(cursor), end: dayEnd });

  Logger.log(`🔄 Updated free gaps after "Get Fit" (${updatedGaps.length}):`);
  updatedGaps.forEach(g =>
    Logger.log(`   gap: ${fmt(g.start)} → ${fmt(g.end)} (${mins(g)} min)`)
  );

  // --- Schedule Wrist stretches (10 min) ---
  if (scheduleWristStretch) {
    let placed = 0;
    const desiredCount = 3;
    const usedTimes = []; // Track used time slots to avoid duplicates

    const ascendingGaps = [...updatedGaps].sort((a, b) => a.start - b.start);
    const descendingGaps = [...updatedGaps].sort((a, b) => b.start - a.start);

    // Helper to check if a time slot overlaps with already used times
    function isTimeUsed(start) {
      return usedTimes.some(used => Math.abs(used - start) < 10 * 60000);
    }

    // 1️⃣ Place one in the middle of the day (as close to noon as possible)
    const noon = new Date(date.getFullYear(), date.getMonth(), date.getDate(), 12, 0);
    let closestGap = null;
    let closestStart = null;
    let closestDistance = Infinity;

    for (const gap of updatedGaps) {
      if (gap.end - gap.start >= 10 * 60000) { // Must fit 10 minutes
        // Try to place the stretch so it's centered around noon
        const idealStart = new Date(noon.getTime() - 5 * 60000); // 5 min before noon
        let candidateStart;
        
        // If ideal time fits in this gap, use it
        if (idealStart >= gap.start && new Date(idealStart.getTime() + 10 * 60000) <= gap.end) {
          candidateStart = idealStart;
        } else if (noon >= gap.start && noon < gap.end) {
          // Noon is in this gap, use gap start or noon (whichever fits)
          candidateStart = gap.start;
        } else {
          // Use the midpoint of the gap
          candidateStart = new Date((gap.start.getTime() + gap.end.getTime()) / 2 - 5 * 60000);
          if (candidateStart < gap.start) candidateStart = gap.start;
        }
        
        const distance = Math.abs(candidateStart - noon);
        
        if (distance < closestDistance) {
          closestDistance = distance;
          closestGap = gap;
          closestStart = candidateStart;
        }
      }
    }

    if (closestGap && closestStart) {
      createPairedEvents("Wrist stretch", closestStart, 10);
      usedTimes.push(closestStart);
      placed++;
      Logger.log(`🕛 Scheduled midday wrist stretch at ${fmt(closestStart)}`);
    }

    // 2️⃣ Place the latest one (as close to 4 pm as possible)
    for (const gap of descendingGaps) {
      if (placed >= desiredCount) break;
      const latestPossibleStart = new Date(gap.end.getTime() - 10 * 60000);
      if (latestPossibleStart >= gap.start && !isTimeUsed(latestPossibleStart)) {
        createPairedEvents("Wrist stretch", latestPossibleStart, 10);
        usedTimes.push(latestPossibleStart);
        placed++;
        Logger.log(`🕓 Scheduled late-day wrist stretch at ${fmt(latestPossibleStart)}`);
        break;
      }
    }

    // 3️⃣ Fill remaining earlier in the day
    for (const gap of ascendingGaps) {
      if (placed >= desiredCount) break;
      let start = gap.start;
      while (placed < desiredCount && start.getTime() + 10 * 60000 <= gap.end.getTime()) {
        if (!isTimeUsed(start)) {
          createPairedEvents("Wrist stretch", start, 10);
          usedTimes.push(start);
          placed++;
          Logger.log(`💪 Scheduled earlier wrist stretch at ${fmt(start)}`);
        }
        start = new Date(start.getTime() + 90 * 60000);
      }
    }

    if (placed < desiredCount)
      Logger.log(`⚠️ Only scheduled ${placed}/${desiredCount} Wrist stretches on ${dayStr}`);
    else
      Logger.log(`✅ Scheduled all ${desiredCount} Wrist stretches for ${dayStr}`);
  } else {
    Logger.log(`⭐️ Skipping "Wrist stretch" events (disabled)`);
  }
}

// NEW FUNCTION: Schedule leg stretch events at 6am and 8pm
function scheduleLegStretchEvents(date, myCal, seriesId, dryRun) {
  const dayStr = date.toDateString();
  
  // Check if leg stretch events already exist for this day
  const existingLegStretches = myCal
    .getEventsForDay(date)
    .filter(e => e.getTitle().includes("Leg stretch and exercise"));
  
  if (existingLegStretches.length >= 2) {
    Logger.log(`🦵 Leg stretch events already exist for ${dayStr} (${existingLegStretches.length} found)`);
    return;
  }
  
  const times = [
    { hour: 6, minute: 0, label: "morning" },
    { hour: 20, minute: 0, label: "evening" }
  ];
  
  times.forEach(time => {
    const start = new Date(date.getFullYear(), date.getMonth(), date.getDate(), time.hour, time.minute);
    const end = new Date(start.getTime() + 15 * 60000); // 15 minutes
    const fullTitle = "[Wellness] Leg stretch and exercise";
    const desc = `Auto-created wellness event (${seriesId})`;
    
    // Check if this specific time already has a leg stretch event
    const existingAtThisTime = existingLegStretches.some(e => 
      e.getStartTime().getHours() === time.hour && 
      e.getStartTime().getMinutes() === time.minute
    );
    
    if (existingAtThisTime) {
      Logger.log(`🦵 Leg stretch already exists at ${fmt(start)} on ${dayStr}`);
      return;
    }
    
    if (dryRun) {
      Logger.log(`💡 Would create "${fullTitle}" at ${fmt(start)} → ${fmt(end)} (${time.label})`);
    } else {
      myCal.createEvent(fullTitle, start, end, {
        description: desc,
        reminders: { useDefault: false, overrides: [] },
      });
      Logger.log(`✅ Created "${fullTitle}" at ${fmt(start)} → ${fmt(end)} (${time.label})`);
    }
  });
}

//
// Helpers
//
function fmt(d) {
  return Utilities.formatDate(d, Session.getScriptTimeZone(), "h:mm a");
}
function mins(g) {
  return Math.round((g.end - g.start) / 60000);
}
function isAllDay(event) {
  const start = event.getStartTime();
  const end = event.getEndTime();
  const dur = end - start;
  // Treat events that start/end at midnight or last >= 20h as all-day
  return (
    dur >= 20 * 60 * 60 * 1000 ||
    (start.getHours() === 0 && start.getMinutes() === 0 && end.getHours() === 0 && end.getMinutes() === 0)
  );
}

function removeAllWellnessEvents() {
  const { myCalendar, workCalendar } = getCalendars();
  
  const startDate = new Date();
  // remove past year
  // startDate.setFullYear(startDate.getFullYear() - 1);
  // remove from today forward
  startDate.setHours(0, 0, 0, 0);

  const endDate = new Date();
  endDate.setDate(endDate.getDate() + 30);

  const myEvents = myCalendar.getEvents(startDate, endDate);
  const workEvents = workCalendar ? workCalendar.getEvents(startDate, endDate) : [];

  myEvents.forEach(event => {
    if (event.getTitle().includes("[Wellness]") || event.getDescription().includes("Auto-created wellness event")) {
      Logger.log(`Deleting event "${event.getTitle()}" from ${myCalendar.getName()}`);
      event.deleteEvent();
    }
  });

  workEvents.forEach(event => {
    // Only delete "Block" events that have the wellness description
    if (event.getTitle() === "Block" && event.getDescription().includes("Auto-blocked for personal wellness")) {
      Logger.log(`Deleting event "${event.getTitle()}" from ${workCalendar.getName()}`);
      event.deleteEvent();
    }
  });
}