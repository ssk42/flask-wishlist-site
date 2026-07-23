import SwiftUI
import WishlistKit

struct LoginView: View {
    let session: Session
    @State private var email = ""
    @State private var familyCode = ""
    @State private var loggingIn = false
    @State private var failed = false

    var body: some View {
        VStack(spacing: 20) {
            Spacer()
            Text("Wishlist").font(.largeTitle.bold())
            Text("Sign in with your email and family code.")
                .font(.subheadline).foregroundStyle(.secondary)
            TextField("Email", text: $email)
                .textContentType(.emailAddress)
                .keyboardType(.emailAddress)
                .autocorrectionDisabled()
                .textInputAutocapitalization(.never)
            SecureField("Family code", text: $familyCode)
            if failed {
                Text("Login failed. Check your email and family code.")
                    .foregroundStyle(.red).font(.footnote)
            }
            Button(action: submit) {
                if loggingIn {
                    ProgressView()
                } else {
                    Text("Log In").frame(maxWidth: .infinity)
                }
            }
            .buttonStyle(.borderedProminent)
            .disabled(email.isEmpty || familyCode.isEmpty || loggingIn)
            Spacer()
        }
        .textFieldStyle(.roundedBorder)
        .padding()
    }

    private func submit() {
        loggingIn = true
        failed = false
        Task {
            let ok = await session.logIn(email: email, familyCode: familyCode)
            loggingIn = false
            failed = !ok
        }
    }
}
