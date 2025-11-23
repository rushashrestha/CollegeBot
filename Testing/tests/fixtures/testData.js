export const CREDENTIALS = {
  valid: {
    email: process.env.EMAIL,
    password: process.env.PASSWORD,
  },
  invalid: {
    email: "rusha@gmail.com",
    password: "ifhdjhfjfhgjdf",
  },

  security: {
    sqlInjection: {
      email: "admin' OR '1'='1"
    },
    xss: {
      email: "<img src=x onerror=alert(1)>"
    },
  },
};

export const ERROR_MESSAGES = {
  userNotRegistered: /user not registered/i,
  invalidCredentials: /invalid credentials/i,
  facilityRequired: /facility.*required/i,
  emailRequired: /email.*required/i,
  passwordRequired: /password.*required/i,
  invalidEmail: /value is not a valid email address/i
};
