import { test } from "@playwright/test";
import { LoginTest } from "./Pages/LoginTest.js";   

let login;

test.beforeEach(async ({ page }) => {
  login = new LoginTest(page);
  await login.navigateToLoginPage();
});

test("Login with valid credentials", async () => {
  await login.validLogin(); 
  console.log("Logged in");
});

const negativeTests = [
  { name: "Login with invalid email", action: "invalidEmailLogin", message: "user not registered"},
  { name: "Login with invalid password", action: "invalidPasswordLogin", message: "invalid credentials"}
];

for (const scenario of negativeTests) {
  test(scenario.name, async () => {
    await login[scenario.action]();
    await login.expectToast(scenario.message);
    await login.expectFailure();
  });
}


test("Login with empty credentials", async ({ page }) => {
  await login.clickLoginButton();
  await login.expectErrorMessage( page, [ "facilityRequired", "emailRequired", "passwordRequired"], { timeout: 8000 });
  await login.expectFailure();
});

test("test login with SQL injection attempts", async () => {
  await login.sqlInjectionLogin();
  await login.expectToast("valid email", 8000);
  await login.expectFailure();
});

test("test login with XSS atempt", async () => {
  await login.xxsLogin();
  await login.expectToast("email", 8000);
  await login.expectFailure();
});


