# Instructions

The configuration and installation of Webapp is taken care as part of the Ansible automation workflow in the repository [sup4rnet-config-and-mgmt](https://github.com/sup4rnet/sup4rnet-config-and-mgmt).

This repo only contains the source code of the website for the switch reservation.  
It is built using Flask framework. 

## Backend

User reservations are stored in a csv file under `.data/` folder. Manual edits to the file will be reflected in the dashboard by reloading the webpage.



