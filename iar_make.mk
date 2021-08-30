mode: lib

src:	./src/ephemeris.c
src:	./src/gnss_filter.c
src:	./src/gnss_integrity.c
src:	./src/lambda.c
src:	./src/model.c
src:	./src/print_nmea.c
src:	./src/pvt_eng.c
src:	./src/RingBuffer.c
src:	./src/rtcm.c
src:	./src/rtk_eng.c
src:	./src/rtk_math.c
src:	./src/rtkcmn.c

inc:    ./include
inc:    ./


int: objs

out: objs/gnss_lib
