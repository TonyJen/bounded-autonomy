// Host-test shim for HTTPClient: a URL-keyed stub registry. Every request
// is recorded; responses come from http_stub() registrations (exact match
// first, then longest substring match) so tests control the gateway.
#pragma once
#include "WiFiClientSecure.h"
#include <sstream>

struct HttpStub {
  int code;
  std::string body;
};

void http_reset();
void http_stub(const char* url_substr, int code, const char* body);

struct HttpRequest {
  std::string method;   // GET / POST
  std::string url;
  std::string body;
  std::string token;    // X-Device-Token header seen on the wire
};
extern std::vector<HttpRequest> http_requests;

class HTTPClient {
public:
  template <typename C> void begin(C&, const String& url) { url_ = url; }
  void setTimeout(int) {}
  void addHeader(const char* name, const char* value) {
    if (std::strcmp(name, "X-Device-Token") == 0) token_ = value;
  }
  int POST(const String& body) { return request("POST", body.c_str()); }
  int POST(uint8_t*, size_t) { return request("POST", ""); }
  int GET() { return request("GET", ""); }
  std::istringstream& getStream() { return stream_; }
  void end() {}
private:
  int request(const char* method, const char* body);
  String url_;
  std::string token_;
  std::istringstream stream_;
};
