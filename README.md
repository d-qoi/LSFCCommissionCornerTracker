# Commission Corner Tracker for Lone Star Fur Con

This will do a few things.

## Pages
* Home Page:
  Will advertize the rules and the current event(s).

* Event Page:
  Will display if the Commission Corner is Open or Closed
  Will list the number of current seats available.
  Will list the current Artists
  Will list the time till the next seat is available.
  Will let people get push notifications for the duration of the event.

* Event Management Page
  Will let us set Open and Close times for the day.
  Will let us name the event
  Will let us set default seat time
  Will let us set the default timeout period
  Will list the current artists, with time remaining for each seat
  Will maintain the list of previous artists, as well as highlight any who are on a 'timeout' period
  Will allow us to add an artist
  Will allow us to remove an artist
  Will create a QR code for the artist to scan so they can get to the Artist's Page


* Artist's Page
  Will let an artist who is in a seat add links to their own website.
  Will let an artist who is in a seat update their names, and profile picture or logo
  Will let an artist who is in a seat update the number of commissions they can take.
  Will show how much time they have left.
  Will let them abandon their seats


## Interactions
Account is needed to create events, and as something to save artist info to.

An event is created
Open/Close schedule is set
Number of seats available are set.

Event organizer can choose a seat to add an artist to.
A link is generated with a unique ID.

Artist follows link, and will adopt UUID as an identity for the event, it is now a token.
They can set a 'slug' for the event, which the event page will link to. Slug is tied to the UUID for the event.
They can use the UUID as auth to edit their profiles domain.com/$eventname/artist/$slug

If artist already has a UUID, they can set themselves to a seat when following the link from the event host again.

The server will save the artist info for the duration of an event.

If the artist creates an account, they can save information they set for the event profile to their account.
If they have an account, they can load info from their account to the event profile

Event host can also edit artist event profile
