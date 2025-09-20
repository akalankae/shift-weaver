# Notes about important functions, classes, ... etc

## caldav.davclient.get_davclient() -> caldav.davclient.DAVClient

Return: caldav.davclient.DAVClient
Parameters: url, username, password (all optional)
Erros: NO ERRORS if parameters are wrong 

caldav.davclient.get_davclient() -> client instance
client.principal() -> caldav.collection.Principal (instance)
principal.calendar(name=CALENDAR_NAME) -> caldav.collection.Calendar (instance)
CALENDAR_NAME is optional. If not given first found calendar is returned.

## caldav.davclient.DAVClient.principal() -> caldav.collection.Principal

## caldav.collection.Principal.calendar() -> caldav.collection.Calendar

Parameters:
- name
- cal_id
- cal_url

## caldav.collection.Principal.make_calendar() -> caldav.collection.Calendar



## caldav.collection.Calendar.save() -> self

Save created calendar

## caldav.collection.Calendar.save_event() -> caldav.calendarobjectresource.Event
## caldav.collection.Calendar.save_object(objclass=caldav.calendarobjectresource.Event) -> caldav.calendarobjectresource.Event

This is the way to add a new object (event, todo or journal) to the calendar.

Similar:
- caldav.collection.Calendar.save_journal()
- caldav.collection.Calendar.save_todo()

Parameters:
- objclass: Event or Todo or Journal
- ical: string in icalendar format or icalendar/vobject instance
- no_overwrite: do not overwrite existing CalendarObjectResource
- no_create: do not create a new CalendarObjectResource, update existing
- keyword arguments: key words from icalendar specification such as,
  * dtstart, dtend, summary, uid, rrule, ...
  * alarm_trigger, alarm_action, alarm_attach


## caldav.collection.Calendar.search() [method] -> caldav.calendarobjectresource.CalendarObjectResource

Calendar may have one of 3 kinds of object: event (VEVENT), todo(VTODO), journal(VJOURNAL).
These are called "Calendar Object Resource" in RFC specification.

Parameters:
- event: bool - if True method returns list[caldav.calendarobjectresource.Event]
- todo: bool - if True method returns list[caldav.calendarobjectresource.Todo]
- journal: bool - if True method returns list[caldav.calendarobjectresource.Journal]
- start: datetime.datetime
- end: datetime.datetime
- expand: bool - if True recurrent events are expanded to separate Event objects


## caldav.calendarobjectresource.Event.save() method

Save event in the CalDAV server. If it is an existing event grabbed from the server, it is modified.
When you take the event data with property access: event_data = event.component it is de-coupled from
the data in CalDAV server. To modify it you have to modify it to the new desired value, then assign to
the original component.

```
event_data = event.component        # same as `event.icalendar_component`
start_date = event_data.start
start_date = datetime.datetime(...)
event.component.start = start_date
event.save()
```

Parameters:
- all_recurrences: bool - if True edit the full series of events

## caldav.calendarobjectresource.Event.delete() method

Delete an event from the calendar. Much like Event.save().

## caldav.calendarobjectresource.Event.data (string in icalendar format)

## caldav.calendarobjectresource.Event.icalendar_component [data attribute] (icalendar.ical.Event)
## caldav.calendarobjectresource.Event.component [data attribute] (icalendar.ical.Event)

Both of these are identical. You can access some properties as attributes of an instance (with dot), for example `start`
as instance.start, or keys of a dictionary (with square brackets), for example `summary` as instance["summary"].
Assigning new values to them and saving modifies it on the server as well.

## caldav.calendarobjectresource.Event.icalendar_instance [data attribute] (icalendar.ical.Calendar)


## caldav.collection.Calendar.event_by_uid(uid:INT) [method] -> caldav.calendarobjectresource.Event
## caldav.collection.Calendar.object_by_uid(uid:INT, comp_class=caldav.calendarobjectresource.Event) [method] -> caldav.calendarobjectresource.Event
