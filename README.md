Mount the Master Volume with `aux-gfid-mount`, For example,

    mount -t glusterfs -o aux-gfid-mount localhost:gv1 /mnt/gv1

Run the script with mount path and changelog file path as arguments

    python gen.py /mnt/gv1 CHANGELOG.1470837234

Example Setup Script

    # Create Master Volume and Start
    gluster v create gv1 fvm1:/bricks/b1 force
    gluster v start gv1

    # Create Slave Volume and Start
    gluster v create gv2 fvm1:/bricks/b2 force
    gluster v start gv2

    # Create Geo-rep session, Start it. Stop the session once
    # it reaches to Changelog Crawl
    gluster system:: execute gsec_create
    gluster v geo gv1 fvm1::gv2 create push-pem
    gluster v geo gv1 fvm1::gv2 start
    sleep 30
    gluster v geo gv1 fvm1::gv2 status
    gluster v geo gv1 fvm1::gv2 stop

    # Mount the Master Volume for Workload creation
    mount -t glusterfs -o aux-gfid-mount localhost:gv1 /mnt/gv1

    cd /root/gluster_changelog_to_workload/
    # Generate list of changelog files for which workload simulation required
    ls changelogs/CHANGELOG.* > all_changelogs.txt
    tail -500 all_changelogs.txt > last_500_changelogs.txt

    # Generate Workload
    cat /root/last_500_changelogs.txt | while read LINE; do python gen.py /mnt/gv1 "/root/changelogs/$LINE"; sleep 1; done

Once the above steps are complete,

    - Set the Checkpoint (gluster v geo gv1 fvm1::gv2 config checkpoint now)
    - Touch the mount point (touch /mnt/gv1)
    - Start Geo-replication (gluster v geo gv1 fvm1::gv2 start)
    - Watch the Geo-rep status for checkpoint status
    - Once Checkpoint status says completed, then
      Duration = Checkpoint Completion Time - Checkpoint Start Time
    - Stop Geo-replication


## Other Helper scripts

To See workload pattern

    #!/usr/bin/env bash
    echo > /tmp/parsed_changelogs
    cat /root/last_500_changelogs.txt | while read LINE; do glustertool changelogparser "/root/changelogs/$LINE" >> /tmp/parsed_changelogs; done
     
    echo "Creates: "$(grep "CREATE" /tmp/parsed_changelogs | wc -l)
    echo "Data   : "$(grep " D " /tmp/parsed_changelogs | wc -l)
    echo "Unlinks: "$(grep "UNLINK" /tmp/parsed_changelogs | wc -l)
    echo "Dirs   : "$(grep "MKDIR" /tmp/parsed_changelogs | wc -l)
    echo "Meta   : "$(grep " M " /tmp/parsed_changelogs | wc -l)

To check number of batches in the generated changelogs directory

    #!/usr/bin/env python
    import os

    BRICK_ROOT = "/bricks/b1/"
    MAX_CHANGELOG_BATCH_SIZE = 727040
    CHANGELOGS_PATH = BRICK_ROOT + ".glusterfs/changelogs"
     
    batches = []
    c = 0
     
    for f in os.listdir(CHANGELOGS_PATH):
        if f.startswith("CHANGELOG."):
            c += os.lstat(os.path.join(CHANGELOGS_PATH, f)).st_size
            if c > MAX_CHANGELOG_BATCH_SIZE:
                batches.append(c)
                c = 0
     
    if c > 0:
        batches.append(c)
     
    print len(batches), batches
