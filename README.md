Mount the Master Volume with `aux-gfid-mount`, For example,

    mount -t glusterfs -o aux-gfid-mount localhost:gv1 /mnt/gv1

Run the script with mount path and changelog file path as arguments

    python gen.py /mnt/gv1 CHANGELOG.1470837234

Run the same script multiple times for each changelog files.

- Once data population is complete, Copy all the changelogs which were used in above script to Brick backend
- Generate HTIME file with copied changelog details.
- Enable changelog and make sure no new HTIME file gets created.
- Establish Geo-rep connection(CREATE)
- Set stime to changelog start time
- Set Checkpoint. and Note the checkpoint set time
- Touch the mount root
- Start Geo-replication
- Once checkpoint is complete, Check the time taken to complete the checkpoint
