# Setting Config File
## slack channel settings
[slack]  
token=token_val  
channel=channel_val

## site user information settings
[user]  
ID=id_val  
passwd=passwd_val

## chrome engine settings
[chrome]  
enginePath=chromedriver_path(absolute)

## set keyword for watching and send alarm.<br/>
[newProducts]  
names=item1&item2
- delimiter is &

## set count for send confirm messege.
[etc]  
watchingSpan=300

<br/>

# How to run the service
1. set your custom data on config file.
2. build docker image
``` shell
~$ sudo docker build -t watchDogs .
```
3. run the service
``` shell
~$ sudo docker run -it watchDogs /home/watchDogs/startServices.sh
