#!/usr/bin/env bash

function test_ok(){
    rc=$?;
    if [[ $rc != 0 ]]; then
        echo "[NOT OK]", $rc, $1;
    else
        echo "[    OK]", $1;
    fi;
}

# Create a Volume with single brick
rm -f changelogdata_%2Fbricks%2Fgvol1_b1.db
gluster --mode=script volume stop gvol1;
gluster --mode=script volume delete gvol1;
rm -rf /bricks/gvol1_b1;
gluster --mode=script volume create gvol1 fvm1:/bricks/gvol1_b1 force;
gluster --mode=script volume start gvol1;
gluster v set gvol1 changelog.changelog on;

# Mount the Volume
umount -f /mnt/gvol1;
mkdir -p /mnt/gvol1;
mount -t glusterfs localhost:/gvol1 /mnt/gvol1;

# Create some files f1 f2 f3 f4 f5 f6 f7 f8 f9 f10
for i in {1..10}
do
    touch /mnt/gvol1/f$i;
done

# Sleep for 15 sec so that Changelog rollover will happen and Note the time(t1)
sleep 15;
t1=$(date +%s);

# Wait for 20 sec and modify some files from previous batch f2 f4 f6 f8 f10
sleep 20;
echo "hello world" > /mnt/gvol1/f2;
echo "hello world" > /mnt/gvol1/f4;
echo "hello world" > /mnt/gvol1/f6;
echo "hello world" > /mnt/gvol1/f8;
echo "hello world" > /mnt/gvol1/f10;

# Create some more files n1 n2 n3 n4 n5 n6 n7 n8 n9 n10
for i in {1..10}
do
    touch /mnt/gvol1/n$i;
done

# Wait for 30 sec
sleep 30;

# Note the time(t2)
t2=$(date +%s);

# Run api to get files which are created/modified before t1 but not after t1
python gchangelogapi.py /bricks/gvol1_b1 -o out1.txt --not-modified-since $t1;

cat > out_expected1.txt <<EOF
00000000-0000-0000-0000-000000000001/f1
00000000-0000-0000-0000-000000000001/f3
00000000-0000-0000-0000-000000000001/f5
00000000-0000-0000-0000-000000000001/f7
00000000-0000-0000-0000-000000000001/f9
EOF

diff out1.txt out_expected1.txt
test_ok "Files Created before $t1"

# Run api to get files which are created/modified before t1 but not after t2
python gchangelogapi.py /bricks/gvol1_b1 -o out2.txt --not-modified-since $t2;

cat > out_expected2.txt <<EOF
00000000-0000-0000-0000-000000000001/f1
00000000-0000-0000-0000-000000000001/f2
00000000-0000-0000-0000-000000000001/f3
00000000-0000-0000-0000-000000000001/f4
00000000-0000-0000-0000-000000000001/f5
00000000-0000-0000-0000-000000000001/f6
00000000-0000-0000-0000-000000000001/f7
00000000-0000-0000-0000-000000000001/f8
00000000-0000-0000-0000-000000000001/f9
00000000-0000-0000-0000-000000000001/f10
00000000-0000-0000-0000-000000000001/n1
00000000-0000-0000-0000-000000000001/n2
00000000-0000-0000-0000-000000000001/n3
00000000-0000-0000-0000-000000000001/n4
00000000-0000-0000-0000-000000000001/n5
00000000-0000-0000-0000-000000000001/n6
00000000-0000-0000-0000-000000000001/n7
00000000-0000-0000-0000-000000000001/n8
00000000-0000-0000-0000-000000000001/n9
00000000-0000-0000-0000-000000000001/n10
EOF

diff out2.txt out_expected2.txt
test_ok "Files Created before $t2"
