# shift-weaver
Intricately and skillfully weaves your shifts into your calendar

## LoginWindow

- Read in user credentials (email ans password) for icloud server from user.
- Launch next window: UploadWindow.
- We have no way of surmising whether entered credentials are correct before
  actually attempting to write to icloud's calendar server.

## UploadWindow

- Allow the user to select the roster file he/she is going to upload and select
  what type of roster it is: term roster or week roster.
- Launch next window: NameSelectWindow.

## NameSelectWindow

-  Ask the user to select his/her name from the list of names found in the
   uploaded roster.
