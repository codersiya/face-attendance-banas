// import EmployeeEnrollForm from "./components/EmployeeEnrollForm.jsx";

// export default function App() {
//   return (
//     <div className="app-shell">
//       <header className="app-header">
//         <div className="app-header__brand">
//           <span className="app-header__mark">FA</span>
//           <span>Face Attendance — Employee Enrollment</span>
//         </div>
//       </header>
//       <main className="app-main">
//         <EmployeeEnrollForm />
//       </main>
//     </div>
//   );
// }
































import EmployeeEnrollForm from "./components/EmployeeEnrollForm.jsx";
import companyLogo from "./logo/aookly.svg"; // Update with your logo path

export default function App() {
  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-header__brand">
          <img
            src={companyLogo}
            alt="Company Logo"
            className="app-header__logo"
          />
          <span>Face Attendance — Employee Enrollment</span>
        </div>
      </header>

      <main className="app-main">
        <EmployeeEnrollForm />
      </main>
    </div>
  );
}