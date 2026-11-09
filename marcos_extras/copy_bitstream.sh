
#!/bin/bash
# Vlad Negnevitsky, October 2020
# Modified to support custom bitstream filenames

if [[ "$#" -lt 2 || "$#" -gt 3 || ($2 != "rp-125" && $2 != "rp-122" ) ]]; then
    echo "Usage: ./copy_bitstream.sh IP DEVICE [BITSTREAM]"
    echo "IP: the IP address of your SDRLab/RP"
    echo "DEVICE: rp-122 or rp-125"
    echo "BITSTREAM: optional custom .bit filename"
    echo "Example:"
    echo "   ./copy_bitstream.sh 192.168.1.163 rp-122"
    echo "   ./copy_bitstream.sh 192.168.1.163 rp-122 marcos_fpga.bit"
    exit 1
fi

BITSTREAM="${3:-marcos_fpga_$2.bit}"

echo "Copying FPGA bitstream: $BITSTREAM"

# Decide which scp command to use
scp readme.org root@$1:/tmp/readme.org >/dev/null 2>/dev/null
if [ "$?" -ne "0" ]; then
    scp_="scp -O"
else
    scp_="scp"
fi

# Check SCP works
$scp_ readme.org root@$1:/tmp/readme.org >/dev/null 2>/dev/null
if [ "$?" -ne "0" ]; then
    echo "SCP command does not run; please investigate manually."
    exit 1
fi

# Decide which Linux image the Red Pitaya is running
rp_uname=$(ssh root@$1 "uname -n")

if [[ $rp_uname == "redpitaya" ]]; then

    echo "Writing bitstream to FPGA, Ocra Linux image"

    $scp_ "$BITSTREAM" root@$1:/lib/firmware/marcos_fpga.bit.bin || exit 1
    $scp_ "${BITSTREAM%.bit}.dtbo" root@$1:/lib/firmware/marcos_fpga.dtbo || exit 1

    echo "(you should see a blue light appear) ..."

    ssh root@$1 <<EOF
#!/bin/bash

if [ -d /sys/kernel/config/device-tree/overlays/full ]; then
    rmdir /sys/kernel/config/device-tree/overlays/full
fi

echo 0 > /sys/class/fpga_manager/fpga0/flags

mkdir /sys/kernel/config/device-tree/overlays/full
echo -n "marcos_fpga.dtbo" > /sys/kernel/config/device-tree/overlays/full/path
EOF

else

    echo "Writing bitstream to FPGA, standard Red Pitaya Linux image"
    echo "(you should see a blue light appear) ..."

    $scp_ "$BITSTREAM" root@$1:/tmp/marcos_fpga.bit || exit 1

    ssh root@$1 <<EOF
cat /tmp/marcos_fpga.bit > /dev/xdevcfg
rm /tmp/marcos_fpga.bit
EOF

fi
