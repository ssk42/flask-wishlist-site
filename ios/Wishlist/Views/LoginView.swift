import SwiftUI
import WishlistKit

struct LoginView: View {
    let session: Session
    @State private var email = ""
    @State private var familyCode = ""
    @State private var loggingIn = false
    @State private var failed = false
    @State private var appeared = false

    var body: some View {
        ZStack {
            Color.wlBg.ignoresSafeArea()
            RadialGradient(colors: [Color.wlAccentSoft.opacity(0.7), .clear],
                           center: .top, startRadius: 0, endRadius: 400)
                .ignoresSafeArea()

            VStack(spacing: 0) {
                Spacer()
                VStack(spacing: 10) {
                    Image(systemName: "gift.fill")
                        .font(.system(size: 32))
                        .foregroundStyle(Color.wlAccent)
                        .padding(.bottom, 4)
                    Text("Wishlist")
                        .font(.wlDisplay(54))
                        .foregroundStyle(Color.wlInk)
                    Text("Gifts, coordinated — surprises kept.")
                        .font(.callout)
                        .foregroundStyle(Color.wlSecondary)
                }
                .opacity(appeared ? 1 : 0)
                .offset(y: appeared ? 0 : 14)

                Spacer().frame(height: 46)

                VStack(spacing: 14) {
                    field("Email", text: $email, icon: "envelope")
                        .textContentType(.emailAddress).keyboardType(.emailAddress)
                        .autocorrectionDisabled().textInputAutocapitalization(.never)
                    field("Family code", text: $familyCode, icon: "key", secure: true)

                    if failed {
                        Label("Login failed. Check your email and family code.",
                              systemImage: "exclamationmark.triangle.fill")
                            .font(.footnote).foregroundStyle(Color.wlAccent)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .transition(.opacity)
                    }

                    Button(action: submit) {
                        Group {
                            if loggingIn { ProgressView().tint(.white) }
                            else { Text("Log In").font(.headline) }
                        }
                        .frame(maxWidth: .infinity).frame(height: 54)
                        .background(Color.wlAccent, in: RoundedRectangle(cornerRadius: 15, style: .continuous))
                        .foregroundStyle(.white)
                        .opacity(canSubmit ? 1 : 0.45)
                    }
                    .disabled(!canSubmit)
                    .padding(.top, 4)
                }
                .opacity(appeared ? 1 : 0)
                .offset(y: appeared ? 0 : 22)

                Spacer(); Spacer()
            }
            .padding(.horizontal, 28)
        }
        .animation(.easeInOut(duration: 0.25), value: failed)
        .onAppear { withAnimation(.easeOut(duration: 0.65)) { appeared = true } }
    }

    private var canSubmit: Bool { !email.isEmpty && !familyCode.isEmpty && !loggingIn }

    @ViewBuilder
    private func field(_ placeholder: String, text: Binding<String>, icon: String, secure: Bool = false) -> some View {
        HStack(spacing: 12) {
            Image(systemName: icon).foregroundStyle(Color.wlSecondary).frame(width: 20)
            Group {
                if secure { SecureField(placeholder, text: text) }
                else { TextField(placeholder, text: text) }
            }
            .foregroundStyle(Color.wlInk)
        }
        .padding(.horizontal, 16).frame(height: 54)
        .background(Color.wlSurface, in: RoundedRectangle(cornerRadius: 15, style: .continuous))
        .overlay(RoundedRectangle(cornerRadius: 15, style: .continuous)
            .strokeBorder(Color.wlHairline, lineWidth: 1))
    }

    private func submit() {
        loggingIn = true; failed = false
        Task {
            let ok = await session.logIn(email: email, familyCode: familyCode)
            loggingIn = false; failed = !ok
        }
    }
}
