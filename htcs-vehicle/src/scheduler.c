#include "scheduler.h"
#if defined(_WIN32)
// Windows Implementation
#include <windows.h>

void startRunning(const int* keepRunning, int intervalMs, void(*callback)())
{
    while (*keepRunning) {
        callback();
        Sleep(intervalMs);
    }
}

#else
// Linux RT implementation
#include <stdio.h>
#include <signal.h>
#include <unistd.h>
#include <time.h>
#include <sched.h>

timer_t timerID;

typedef struct {
    int* keepRunning;
    void (*callback)();
} sigval;

void handlerTimer(int signal, siginfo_t *si, void* uc)
{
    sigval* sv = si->si_value.sival_ptr;
    if (sv->keepRunning) {
        sv->callback();
    } else {
        timer_delete(timerID);
        raise(SIGUSR1);
    }
}

void startRunning(int* keepRunning, int intervalMs, void(*callback)())
{
    struct sched_param schedpar;
    schedpar.sched_priority = 12;

    //Requires root access
    if (sched_setscheduler(getpid(), SCHED_RR, &schedpar)) {
        perror("Failed to set scheduler");
    }

    sigval sv;
    sv.keepRunning = keepRunning;
    sv.callback = callback;

    struct sigevent sigev;
    sigev.sigev_notify = SIGEV_SIGNAL;
    sigev.sigev_signo = SIGRTMIN + 6;
    sigev.sigev_value.sival_ptr = &sv;

    if (timer_create(CLOCK_REALTIME, &sigev, &timerID)) {
        perror("Failed to create timer");
        *keepRunning = 0;
    }

    //Register signal handler
    struct sigaction sigact;
    sigemptyset(&sigact.sa_mask);
    sigact.sa_sigaction = handlerTimer;
    sigact.sa_flags = SA_SIGINFO;
    sigaction(SIGRTMIN + 6, &sigact, NULL);

    struct itimerspec timer;
    timer.it_interval.tv_sec = intervalMs / 1000;
    timer.it_interval.tv_nsec = (intervalMs % 1000) * 1000000;
    timer.it_value.tv_sec = timer.it_interval.tv_sec;
    timer.it_value.tv_nsec = timer.it_interval.tv_nsec;

    timer_settime(timerID, 0, &timer, NULL);

    sigset_t mask, oldmask;
    sigemptyset(&mask);
    sigaddset(&mask, SIGUSR1);
    sigprocmask(SIG_BLOCK, &mask, &oldmask);
    while (*keepRunning) {
        sigsuspend(&mask);
    }
    sigprocmask(SIG_BLOCK, &mask, NULL);
}

#endif
