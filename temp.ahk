Run "bash --login -i",,, &id1
WinWait "ahk_pid " id1
WinActivate
WinMove A_Screenwidth*0.6, A_ScreenHeight*0.6, A_ScreenWidth*0.3, A_ScreenHeight*0.3
Send "source '/c/Users/huseyin.yigit/Desktop/GitHub/SignalRegistry/registry-api/bootstrap.sh' initialize{Enter}"
