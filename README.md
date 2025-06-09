# MPI-Scraper

### Local dev test

Start the selenium hub on local computer:

```sh
docker run --rm -it -p 4444:4444 -p 7900:7900  \
  -e SE_OPTS='--enable-managed-downloads true' \
  -e SE_VNC_NO_PASSWORD=1 \
  --shm-size 2g selenium/standalone-edge:128.0 
```