#include "command.h"
#include <stdio.h>
#include <signal.h>

void processCommand(const Command cmd, State* state) {
    switch (cmd) {
        case MAINTAIN_SPEED:
            printf("Maintain speed command received\n");
            state->accelerationState = MAINTAINING_SPEED;
            break;
        case ACCELERATE:
            printf("Accelerate command received\n");
            state->accelerationState = ACCELERATING;
            break;
        case BRAKE:
            printf("Brake command received\n");
            state->accelerationState = BRAKING;
            break;
        case CHANGE_LANE:
            printf("Change lane command received\n");
            switch (state->lane) {
                case MERGE_LANE:
                    state->lane = MERGE_TO_TRAFFIC;
                    break;
                case TRAFFIC_LANE:
                    state->lane = TRAFFIC_TO_EXPRESS;
                    break;
                case EXPRESS_LANE:
                    state->lane = EXPRESS_TO_TRAFFIC;
                    break;
                default:
                    printf("Already changing lane\n");
            }
            break;
        case TERMINATE:
            printf("Terminate command received\n");
            fflush(stdout);
            raise(SIGTERM);
            break;
        default:
            printf("Unknown command received\n");
    }
    fflush(stdout);
}
