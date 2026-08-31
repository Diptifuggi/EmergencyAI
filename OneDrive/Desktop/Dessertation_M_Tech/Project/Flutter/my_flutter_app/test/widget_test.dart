import 'package:flutter_test/flutter_test.dart';
import 'package:my_flutter_app/main.dart';

void main() {
  testWidgets('EmergencyIQ app loads', (WidgetTester tester) async {
    await tester.pumpWidget(const EmergencyIqApp());
    await tester.pump();
    expect(find.text('Emergency Report'), findsOneWidget);
  });
}