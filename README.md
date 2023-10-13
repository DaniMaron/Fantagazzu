# Fantasy Football

#### Demo: https://fantagazzu.pythonanywhere.com/
#### Username: Demo
#### Password: Demonstration2023

#### Video Demo:  <https://youtu.be/XEgfTp1zDkY>

#####
My final project is a Web Application to check and manage players and teams before and during a Fantasy Football auction (Italian Serie A League).

The user will land in a "Login" page by default, but there is also the option to register as a new user.
While the Login page is pretty standard, in order to register as a new user a "league code" is required.
This is because the website will be put online soon but it is intended for a selected group of friends of mine only at this stage,
so the code prevents unwanted people from registering.

Once logged in, the user lands in the "League" page, which contains a collapsible element for each registered user, displaying their name, the number of players acquired for each role, and the tokens balance.
When expanded, the collapsible will show all players belongin to that specific user, and it will be possible to click on them in order
to open a modal which contains statistics from the previous season, a Sell Button and a "Star/Unstar" Button to add to / remove from the favourites.

On the top of the page there's a "FANTAGAZZU" logo, which when clicked sends the user to the "Players" page.  This is a list of all
players participating in the tournament for the upcoming season. They've previously been uploaded into a database file using a CSV file from the FIFA website.
There's a Search Box at the top which stays there when scrolling the page and can be used to look for specific players. They can also be ordered in ascending and descending order according to different criteria using the table head buttons.
Clicking on the players once again opens a modal with stats, "Buy/Sell" button and "Star/Unstar" button according to the circumstances.

Next to the logo there are other links to different pages.
The "Favourites" page is basically the same as the players one, except it only features players that have been starred by the user.

The "My Team" page is also quite similar to the other two. It features all the players that belong to the user but on top it also has a count of how many Forwards, Defenders, Midfielders, Goalkeeper the user has got so far. And on the right corner there's the tokens balance.

The next link at the top sends the user to a page called "Transactions", which displays every single transaction that has been
executed by any user, specifying if the player was bought or sold, for how much, and at what time and date.
This has been added to the site to keep track of eventual errors and to ensure the whole process is done fairly and transparently.

The last link is a "Log Out" link, which simply logs the user out and ends the session.