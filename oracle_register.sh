#!/bin/bash
# Oracle Cloud Free Tier Registration
# No credit card required for Always Free tier

echo "=== Oracle Cloud Free Tier Setup ==="
echo ""
echo "1. Go to: https://cloud.oracle.com"
echo "2. Click 'Sign Up for Free Tier'"
echo "3. Use email: iwepnewqviay800@gmail.com"
echo "4. Complete registration"
echo "5. Create Compute Instance:"
echo "   - Image: Ubuntu 22.04"
echo "   - Shape: Ampere ARM (4 OCPU/24GB)"
echo ""
echo "6. SSH Public Key:"
cat /root/.ssh/oracle_key.pub
echo ""
echo "7. After creating instance, get Public IP"
echo "8. Connect: ssh -i /root/.ssh/oracle_key ubuntu@<IP>"
echo "9. Set password: sudo passwd ubuntu"
echo ""
echo "10. Send to Telegram: add vps oracle <IP> <Password>"
