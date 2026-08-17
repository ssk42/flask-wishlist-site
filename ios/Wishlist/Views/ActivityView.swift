import SwiftUI
import WishlistKit

struct ActivityView: View {
    let client: APIClient
    @State private var vm: ActivityViewModel

    init(client: APIClient) {
        self.client = client
        _vm = State(initialValue: ActivityViewModel(client: client))
    }

    var body: some View {
        NavigationStack {
            ZStack {
                Color.wlBg.ignoresSafeArea()
                VStack(spacing: 0) {
                    WLScreenTitle("Activity") {
                        if vm.unreadCount > 0 {
                            Button("Read all") { Task { await vm.markAllRead() } }
                                .font(.subheadline.weight(.medium))
                                .foregroundStyle(Color.wlAccent)
                        }
                    }

                    if vm.notifications.isEmpty && !vm.isLoading {
                        Spacer()
                        ContentUnavailableView("All caught up", systemImage: "bell",
                                               description: Text("Claims, comments, and price drops show up here."))
                        Spacer()
                    } else {
                        List {
                            if let error = vm.error {
                                Text(error).font(.footnote).foregroundStyle(Color.wlAccent)
                                    .listRowBackground(Color.clear).listRowSeparator(.hidden)
                            }
                            ForEach(vm.notifications) { notification in
                                Button { Task { await vm.markRead(notification) } } label: {
                                    HStack(spacing: 12) {
                                        Circle()
                                            .fill(notification.isRead ? Color.clear : Color.wlAccent)
                                            .frame(width: 8, height: 8)
                                        Text(notification.message)
                                            .font(notification.isRead ? .subheadline : .subheadline.weight(.semibold))
                                            .foregroundStyle(notification.isRead ? Color.wlSecondary : Color.wlInk)
                                            .multilineTextAlignment(.leading)
                                        Spacer()
                                    }
                                    .wlCard(padding: 14)
                                }
                                .buttonStyle(WLCardButtonStyle())
                                .listRowInsets(.init(top: 5, leading: 18, bottom: 5, trailing: 18))
                                .listRowSeparator(.hidden)
                                .listRowBackground(Color.clear)
                            }
                        }
                        .listStyle(.plain)
                        .scrollContentBackground(.hidden)
                        .refreshable { await vm.load() }
                    }
                }
            }
            .navigationTitle("")
            .navigationBarTitleDisplayMode(.inline)
            .task { if vm.notifications.isEmpty { await vm.load() } }
            .onChange(of: vm.unreadCount) { _, count in
                // One hook covers initial load and both markRead/markAllRead paths.
                // @spec IOS-ACT-010
                PushManager.shared.syncBadge(unreadCount: count)
            }
        }
        .tint(.wlAccent)
    }
}
