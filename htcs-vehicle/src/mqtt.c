#include "mqtt.h"
#if !defined(_WIN32)
#include <unistd.h>
#else
#include <windows.h>
#endif
#include <string.h>

MQTTAsync createAndConnect(const char* address, const char* username, const char* password,
        const char* client_id, const int* keepRunning)
{
    MQTTAsync client;
    int rc;
    if ((rc = MQTTAsync_create(&client, address, client_id, MQTTCLIENT_PERSISTENCE_NONE, NULL)) != MQTTASYNC_SUCCESS)
    {
        printf("Failed to create client object, return code %d\n", rc);
        return NULL;
    }

    if ((rc = MQTTAsync_setCallbacks(client, NULL, connectionLost, messageArrived, NULL)) != MQTTASYNC_SUCCESS)
    {
        printf("Failed to set callback, return code %d\n", rc);
        return NULL;
    }

    MQTTAsync_connectOptions conn_opts = MQTTAsync_connectOptions_initializer;
    conn_opts.keepAliveInterval = 20;
    conn_opts.cleansession = 1;
    conn_opts.username = username;
    conn_opts.password = password;
    conn_opts.onSuccess = onConnect;
    conn_opts.onFailure = onConnectFailure;
    int connected = 0;
    conn_opts.context = &connected;
    if ((rc = MQTTAsync_connect(client, &conn_opts)) != MQTTASYNC_SUCCESS)
    {
        printf("Failed to start connect, return code %d\n", rc);
        return NULL;
    }

    printf("Waiting for connection to %s\n", address);
    while (!connected && *keepRunning)
    {
        #if defined(_WIN32)
        Sleep(100);
        #else
        usleep(10000L);
        #endif
    }
    return client;
}

void onConnect(void* connected, MQTTAsync_successData* response)
{
    printf("Successful connection\n");
    *((int*)connected) = 1;
}

void onConnectFailure(void* context, MQTTAsync_failureData* response)
{
    printf("Connect failed, rc: %d, message: %s\n",
            response ? response->code : 0, response ? response->message : "unknown");
}

void connectionLost(void *context, char *cause)
{
    MQTTAsync client = (MQTTAsync)context;
    MQTTAsync_connectOptions conn_opts = MQTTAsync_connectOptions_initializer;
    int rc;

    printf("\nConnection lost\n");
    printf("     cause: %s\n", cause);

    printf("Reconnecting\n");
    conn_opts.keepAliveInterval = 20;
    conn_opts.cleansession = 1;
    if ((rc = MQTTAsync_connect(client, &conn_opts)) != MQTTASYNC_SUCCESS)
    {
        printf("Failed to start connect, return code %d\n", rc);
    }
}

void disconnect(MQTTAsync client, MQTTAsync_failureData* response)
{
    MQTTAsync_disconnectOptions opts = MQTTAsync_disconnectOptions_initializer;
    int rc;

    if (response != NULL)
    {
        printf("Message send failed token %d error code %d\n", response->token, response->code);
    }
    opts.onSuccess = onDisconnect;
    opts.onFailure = onDisconnectFailure;
    opts.context = client;
    if ((rc = MQTTAsync_disconnect(client, &opts)) != MQTTASYNC_SUCCESS)
    {
        printf("Failed to start disconnect, return code %d\n", rc);
    }
    MQTTAsync_destroy(&client);
}

void onDisconnect(void* context, MQTTAsync_successData* response)
{
    printf("Successful disconnection\n");
}

void onDisconnectFailure(void* context, MQTTAsync_failureData* response)
{
    printf("Disconnect failed\n");
}

int sendMessage(MQTTAsync client, char* topic, char* payload)
{
    MQTTAsync_responseOptions opts = MQTTAsync_responseOptions_initializer;
    opts.onSuccess = onSend;
    opts.context = client;

    MQTTAsync_message message = MQTTAsync_message_initializer;
    message.payload = payload;
    message.payloadlen = (int)strlen(payload);
    message.qos = 1;
    message.retained = 0;
    int rc;
    if ((rc = MQTTAsync_sendMessage(client, topic, &message, &opts)) != MQTTASYNC_SUCCESS)
    {
        printf("Failed to start sendMessage, return code %d\n", rc);
    }
    return rc;
}

void onSend(void* context, MQTTAsync_successData* response)
{
    printf("Message with token value %d delivery confirmed\n", response->token);
}

int messageArrived(void* context, char* topicName, int topicLen, MQTTAsync_message* m)
{
    /* not expecting any messages */
    return 1;
}
