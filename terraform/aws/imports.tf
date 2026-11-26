# These import existing resources. Review the plan before applying.
import {
  to = aws_security_group.app
  id = "sg-003eb6de1e24f2245"
}

import {
  to = aws_instance.app
  id = "i-0b11885ca25eaa3c0"
}
