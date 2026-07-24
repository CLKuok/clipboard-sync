import SwiftUI

struct ContentView: View {
    var body: some View {
        VStack(spacing: 12) {
            Image(systemName: "clipboard")
                .font(.largeTitle)
            Text("Clipboard Sync")
                .font(.title)
            Text("iPhone app baseline")
                .foregroundStyle(.secondary)
        }
        .padding()
    }
}

#Preview {
    ContentView()
}
