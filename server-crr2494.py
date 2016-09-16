import sys
from socket import *
import time
import os.path

# Notes: does not check for carriage at end of each line
# Also does not check validity of headers it doesn't care about
# Everything else should be fine, as far as I know.

# Function definitions


def construct_message(n, file_name, extension):
    status_phrase = ''
    if n == 200:
        status_phrase = 'OK'
    if n == 400:
        status_phrase = 'Bad Request'
    if n == 404:
        status_phrase = 'Not Found'
    if n == 304:
        status_phrase = 'Not Modified'
    if n == 505:
        status_phrase = 'HTTP Version Not Supported'

    status_line = 'HTTP/1.1 ' + str(n) + ' ' + status_phrase + '\r\n'
    tnow = time.gmtime()
    tnowstr = 'Date: ' + time.strftime('%a, %d %b %Y %H:%M:%S %Z', tnow) + '\r\n'
    server_line = 'Server: localhost/127.0.0.1\r\n'
    if (file_name == '') | (n == 404):
        last_modified_line = 'Last-Modified: none\r\n'
    else:
        last_modified_line = 'Last-Modified: ' + time.strftime('%a, %d %b %Y %H:%M:%S %Z',
                                                               time.gmtime(os.path.getmtime(file_name))) + '\r\n'
    accept_ranges_line = 'Accept-Ranges: bytes\r\n'
    content_type_line = ''
    if extension == 'txt':
        content_type_line = 'Content-Type: text/plain\r\n'
    if (extension == 'html') | (extension == 'htm'):
        content_type_line = 'Content-Type: text/html\r\n'
    if (extension == 'jpg') | (extension == 'jpeg'):
        content_type_line = 'Content-Type: image/jpeg\r\n'

    if (file_name == '') | (n == 404):
        content_length_line = 'Content-Length: 0\r\n'
    else:
        content_length_line = 'Content-Length: ' + str(os.path.getsize(file_name)) + '\r\n'

    connection_line = 'Connection: close\r\n'
    response_message = status_line + tnowstr + server_line + last_modified_line + accept_ranges_line + \
                       content_length_line + connection_line + content_type_line + '\r\n'
    return response_message


# code from lecture slides
def get_time(time_string):
    print(time_string)
    date = time.strptime(time_string, '%a, %d %b %Y %H:%M:%S %Z')

    return date


# Server port from command line arg
serverPort = int(sys.argv[1])

serverSocket = socket(AF_INET, SOCK_STREAM)
serverSocket.bind(('', serverPort))
serverSocket.listen(1)

print('The server is ready to receive')


while 1:
    connectionSocket, addr = serverSocket.accept()
    rawMessage = connectionSocket.recv(8192)
    message = bytes.decode(rawMessage)
    length = len(message)
    print("Request: " + message)
    if length == 0:
        # weird chrome thing
        connectionSocket.close()
        continue

    lines = message.split('\r\n')
    first_line_parts = lines[0].split(' ')
    request = ''
    url = ''
    http_version = ''
    file = ''
    file_extension = ''
    file_not_found = False
    bad_request = False
    malformed_request = True
    conditional_get = False
    get = False
    file_is_modified = False
    file_modified_check = 0
    file_last_modified = 0
    version_unsupported = False
    status_code = 0

    if len(first_line_parts) == 3:
        request = first_line_parts[0]
        url = first_line_parts[1]
        http_version = first_line_parts[2]
    else:
        malformed_request = True

    if http_version != 'HTTP/1.1':
        version_unsupported = True

    if request == 'GET':
        get = True
        filename = url[1:]
        if filename == '':
            filename = 'index.html'
        if filename != '':
            file_extension = (filename.split('.'))[1]
        # look for file
        try:
            file = open(filename, 'r')
        except IOError:
            file_not_found = True

        for l in lines:
            l_parts = l.split(' ')
            if l_parts[0] == 'Host:':
                malformed_request = False
            if l_parts[0] == 'If-Modified-Since:':
                conditional_get = True
                if len(l_parts) == 6:
                    file_modified_string = l_parts[1] + ' ' + l_parts[2] + ' ' + l_parts[3] + ' ' + \
                                       l_parts[4] + ' ' + l_parts[5] + ' ' + l_parts[6]
                else:
                    file_modified_string = l_parts[1] + ' ' + l_parts[2] + ' ' + l_parts[3] + ' ' + l_parts[4] \
                                           + ' ' + l_parts[5] + ' ' + l_parts[6] + ' ' + l_parts[7] + ' ' + l_parts[8]
                file_modified_check = get_time(file_modified_string)

    else:
        bad_request = True

    if conditional_get:
        file_last_modified = time.gmtime(os.path.getmtime(filename))
        if file_last_modified > file_modified_check:
            file_is_modified = True

    # case: malformed request
    if malformed_request:
        status_code = 400
        response = construct_message(400, '', file_extension)
        connectionSocket.send(response.encode())
        connectionSocket.close()
        continue

    # case: HTTP version unsupported
    if version_unsupported:
        status_code = 505
        response = construct_message(505, '', file_extension)
        connectionSocket.send(response.encode())
        connectionSocket.close()
        continue

    # case: file not found
    # send an error message
    if file_not_found:
        status_code = 404
        response = construct_message(404, '', file_extension)
        connectionSocket.send(response.encode())
        connectionSocket.close()
        continue

    # case: bad request
    if bad_request:
        status_code = 400
        response = construct_message(400, '', file_extension)
        connectionSocket.send(response.encode())
        connectionSocket.close()
        continue

    # case: conditional GET
    if conditional_get:
        if file_is_modified:
            status_code = 200
            if (file_extension == 'jpg') | (file_extension == 'jpeg'):
                message_body = ''
                file = open(filename, 'rb')
                jpg_contents = file.read()
                response = construct_message(200, filename, file_extension)
                connectionSocket.send(response.encode() + jpg_contents)
            else:
                file_contents = file.read()
                jpg_contents = ''
                message_body = file_contents
                response = construct_message(200, filename, file_extension)
                connectionSocket.send((response + message_body).encode())
            connectionSocket.close()
            continue
        else:
            status_code = 304
            response = construct_message(304, '', file_extension)
            connectionSocket.send(response.encode())
            connectionSocket.close()
            continue

    # case: GET
    if get:
        status_code = 200
        if (file_extension == 'jpg') | (file_extension == 'jpeg'):
            message_body = ''
            file = open(filename, 'rb')
            jpg_contents = file.read()
            response = construct_message(200, filename, file_extension)
            connectionSocket.send(response.encode() + jpg_contents)
        else:
            file_contents = file.read()
            jpg_contents = ''
            message_body = file_contents
            response = construct_message(200, filename, file_extension)
            connectionSocket.send((response + message_body).encode())
        connectionSocket.close()
        continue

    connectionSocket.close()
    continue
