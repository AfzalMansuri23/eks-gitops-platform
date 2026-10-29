# Networking

## Connection refused
Matches: `connection refused`, `econnrefused`, `connect: connection refused`

**Cause.** The host answered but nothing listens on that port: the service is down, bound to 127.0.0.1 only, or listening on a different port. A refusal is fast. A slow failure is a timeout, which is a different problem.

**Fix.** Check the service is running and which address and port it binds to.

```sh
ss -ltnp
curl -v http://<host>:<port>/
nc -zv <host> <port>
```

## Connection timed out
Matches: `connection timed out`, `i/o timeout`, `etimedout`, `operation timed out`

**Cause.** Packets are dropped on the way: a firewall, security group or NetworkPolicy blocks them, there is no route, or the host is down.

**Fix.** Test the port from the client side, then walk the path: client firewall, routing, cloud security groups, host firewall.

```sh
nc -zv -w 5 <host> <port>
traceroute <host>
```

## DNS name does not resolve
Matches: `nxdomain`, `could not resolve host`, `name or service not known`, `no such host`

**Cause.** The name is wrong, the record does not exist yet (or was just created and is cached as missing), or the client uses a resolver that cannot see it (private zones).

**Fix.** Query the name directly against your resolver and a public one to see which side is wrong.

```sh
dig <name>
dig @8.8.8.8 <name>
cat /etc/resolv.conf
```
Tool: DNS

## x509: certificate signed by unknown authority
Matches: `x509: certificate signed by unknown authority`, `unable to get local issuer certificate`, `self-signed certificate in certificate chain`, `certificate verify failed`

**Cause.** The client does not trust the CA that signed the server's certificate: a private CA, a corporate proxy that inspects TLS, or a server that sends an incomplete chain.

**Fix.** Look at the chain the server sends. Add the CA to the client's trust store, or fix the server to send the full chain.

```sh
openssl s_client -connect <host>:443 -servername <host> -showcerts </dev/null
```
Tool: TLS

## TLS certificate has expired
Matches: `certificate has expired`, `cert_has_expired`, `notafter`

**Cause.** The certificate passed its expiry date because renewal failed or was never automated.

**Fix.** Check the dates, renew the certificate, and automate renewal (cert-manager, ACM, Let's Encrypt with a timer).

```sh
echo | openssl s_client -connect <host>:443 -servername <host> 2>/dev/null | openssl x509 -noout -dates
```
Tool: TLS

## Certificate name does not match the host
Matches: `certificate is valid for`, `no alternative certificate subject name matches`, `hostname mismatch`

**Cause.** The certificate's subject alternative names do not include the hostname you connected to.

**Fix.** Check the SANs and issue a certificate that covers the name, or connect with the name it was issued for.

```sh
echo | openssl s_client -connect <host>:443 -servername <host> 2>/dev/null | openssl x509 -noout -ext subjectAltName
```
Tool: TLS

## TLS wrong version number
Matches: `wrong version number`, `http request to an https server`

**Cause.** One side speaks TLS and the other plain HTTP, for example https:// to a port that serves HTTP.

**Fix.** Use the right scheme for the port, or terminate TLS where the client expects it.

```sh
curl -v http://<host>:<port>/
curl -v https://<host>:<port>/
```
Tool: TLS

## cert-manager certificate stuck pending
Matches: `waiting for http-01 challenge propagation`, `challenge`, `certificaterequest`, `acme`
Tool: cert-manager

**Cause.** The ACME challenge cannot complete: DNS does not point at the ingress yet, the ingress class is wrong, port 80 is blocked, or the DNS-01 credentials are wrong.

**Fix.** Follow the chain Certificate, CertificateRequest, Order, Challenge and read the reason on the Challenge.

```sh
kubectl get certificate,certificaterequest,order,challenge -A
kubectl describe challenge <challenge> -n <namespace>
```

## Nginx 502 Bad Gateway
Matches: `502 bad gateway`, `connect() failed (111: connection refused) while connecting to upstream`, `upstream prematurely closed connection`
Tool: Nginx

**Cause.** Nginx could not get a valid response from the upstream: the app is down, listens on a different port, or crashed mid-request.

**Fix.** Read the Nginx error log for the upstream address, then test that address directly.

```sh
sudo tail -n 50 /var/log/nginx/error.log
curl -v http://<upstream-host>:<upstream-port>/
```

## Nginx 504 Gateway Timeout
Matches: `504 gateway time-out`, `upstream timed out (110: connection timed out)`
Tool: Nginx

**Cause.** The upstream did not answer within proxy_read_timeout (60 seconds by default), usually a slow query or a blocked worker.

**Fix.** Find why the backend is slow. Raise proxy_read_timeout only for endpoints that are meant to be long-running.

```sh
sudo tail -n 50 /var/log/nginx/error.log
```

## 413 Request Entity Too Large
Matches: `413 request entity too large`, `client intended to send too large body`
Tool: Nginx

**Cause.** The upload is bigger than client_max_body_size (1 MB by default).

**Fix.** Raise client_max_body_size. On ingress-nginx, set the nginx.ingress.kubernetes.io/proxy-body-size annotation.

```sh
kubectl annotate ingress <ingress> -n <namespace> nginx.ingress.kubernetes.io/proxy-body-size=50m --overwrite
```

## Nginx config fails to load
Matches: `nginx: [emerg]`, `configuration file /etc/nginx/nginx.conf test failed`
Tool: Nginx

**Cause.** A syntax error, an unknown directive, or a missing file (certificate, include) in the config.

**Fix.** Test the config, fix the line it names, then reload.

```sh
sudo nginx -t
sudo systemctl reload nginx
```

## Browser blocked by CORS policy
Matches: `blocked by cors policy`, `no 'access-control-allow-origin' header`
Tool: HTTP API

**Cause.** The API does not return the CORS headers that allow the page's origin, often on the OPTIONS preflight request.

**Fix.** Allow the exact origin on the API (or at the ingress) and make sure OPTIONS requests get the headers too.

```sh
curl -i -X OPTIONS <api-url> -H "Origin: <page-origin>" -H "Access-Control-Request-Method: GET"
```
