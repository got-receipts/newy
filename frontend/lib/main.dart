import 'dart:convert';
// ignore: avoid_web_libraries_in_flutter
import 'dart:html' as html;

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:intl/intl.dart';
import 'package:shared_preferences/shared_preferences.dart';

const apiBaseUrl = String.fromEnvironment('API_BASE_URL', defaultValue: 'http://localhost:8000');
const disclaimer =
    'GigOS is an independent shift, mileage, break, and earnings tracker for gig workers. Not affiliated with Uber, DoorDash, Grubhub, Instacart, Amazon Flex, or any delivery platform.';

void main() {
  runApp(const GigOSApp());
}

class GigOSApp extends StatelessWidget {
  const GigOSApp({super.key});

  @override
  Widget build(BuildContext context) {
    final scheme = ColorScheme.fromSeed(
      seedColor: const Color(0xff32d583),
      brightness: Brightness.dark,
      surface: const Color(0xff151a1f),
    );
    return MaterialApp(
      title: 'GigOS',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: scheme,
        scaffoldBackgroundColor: const Color(0xff101418),
        cardTheme: const CardThemeData(
          color: Color(0xff171d23),
          elevation: 0,
          margin: EdgeInsets.zero,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.all(Radius.circular(8))),
        ),
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: const Color(0xff1d252c),
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: BorderSide.none),
        ),
      ),
      home: const AppRoot(),
    );
  }
}

class ApiClient {
  ApiClient(this.token);
  String? token;

  Map<String, String> get headers => {
        'Content-Type': 'application/json',
        if (token != null) 'Authorization': 'Bearer $token',
      };

  Uri uri(String path) => Uri.parse('$apiBaseUrl$path');

  Future<dynamic> request(String method, String path, {Map<String, dynamic>? body}) async {
    final request = http.Request(method, uri(path));
    request.headers.addAll(headers);
    if (body != null) request.body = jsonEncode(body);
    final streamed = await request.send();
    final response = await http.Response.fromStream(streamed);
    if (response.statusCode >= 400) {
      String detail = 'Request failed';
      try {
        final decoded = jsonDecode(response.body);
        final payload = decoded is Map<String, dynamic> ? decoded['detail'] : decoded;
        if (payload is List && payload.isNotEmpty && payload.first is Map<String, dynamic>) {
          detail = payload.first['msg']?.toString() ?? payload.toString();
        } else {
          detail = payload.toString();
        }
      } catch (_) {}
      throw Exception(detail);
    }
    if (response.body.isEmpty) return null;
    return jsonDecode(response.body);
  }
}

class LogoBadge extends StatelessWidget {
  const LogoBadge({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xff32d583),
        borderRadius: BorderRadius.circular(8),
        boxShadow: const [BoxShadow(color: Color(0x5532d583), blurRadius: 12)],
      ),
      child: const Center(
        child: Text('G', style: TextStyle(color: Color(0xff101418), fontWeight: FontWeight.w900, fontSize: 20)),
      ),
    );
  }
}

class AppRoot extends StatefulWidget {
  const AppRoot({super.key});

  @override
  State<AppRoot> createState() => _AppRootState();
}

class _AppRootState extends State<AppRoot> {
  String? token;
  Map<String, dynamic>? me;
  late ApiClient api;
  bool loading = true;

  @override
  void initState() {
    super.initState();
    api = ApiClient(null);
    _bootstrap();
  }

  Future<void> _bootstrap() async {
    final prefs = await SharedPreferences.getInstance();
    token = prefs.getString('token');
    api.token = token;
    if (token != null) {
      try {
        me = await api.request('GET', '/me') as Map<String, dynamic>;
      } catch (_) {
        await prefs.remove('token');
        token = null;
      }
    }
    setState(() => loading = false);
  }

  Future<void> setSession(String nextToken, Map<String, dynamic> user) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('token', nextToken);
    setState(() {
      token = nextToken;
      api.token = nextToken;
      me = user;
    });
  }

  Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('token');
    setState(() {
      token = null;
      api.token = null;
      me = null;
    });
  }

  @override
  Widget build(BuildContext context) {
    if (loading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    if (token == null) {
      return AuthScreen(api: api, onSession: setSession);
    }
    return HomeShell(api: api, user: me!, onLogout: logout);
  }
}

class AuthScreen extends StatefulWidget {
  const AuthScreen({super.key, required this.api, required this.onSession});
  final ApiClient api;
  final Future<void> Function(String token, Map<String, dynamic> user) onSession;

  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  final email = TextEditingController();
  final password = TextEditingController();
  bool register = false;
  bool busy = false;
  String? error;

  @override
  void dispose() {
    email.dispose();
    password.dispose();
    super.dispose();
  }

  Future<void> submit() async {
    setState(() {
      busy = true;
      error = null;
    });
    try {
      final data = await widget.api.request(
        'POST',
        register ? '/auth/register' : '/auth/login',
        body: {'email': email.text.trim(), 'password': password.text},
      ) as Map<String, dynamic>;
      await widget.onSession(data['access_token'] as String, data['user'] as Map<String, dynamic>);
    } catch (err) {
      setState(() => error = err.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(20),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 430),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Text('GigOS', style: TextStyle(fontSize: 44, fontWeight: FontWeight.w800)),
                  const SizedBox(height: 8),
                  Text('Independent shift intelligence for gig work.', style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 28),
                  TextField(controller: email, keyboardType: TextInputType.emailAddress, decoration: const InputDecoration(labelText: 'Email')),
                  const SizedBox(height: 12),
                  TextField(controller: password, obscureText: true, decoration: const InputDecoration(labelText: 'Password')),
                  if (error != null) ...[
                    const SizedBox(height: 12),
                    Text(error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
                  ],
                  const SizedBox(height: 18),
                  FilledButton(
                    onPressed: busy ? null : submit,
                    style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(56)),
                    child: Text(busy ? 'Working...' : register ? 'Create Account' : 'Login'),
                  ),
                  TextButton(
                    onPressed: () => setState(() => register = !register),
                    child: Text(register ? 'Have an account? Login' : 'Need an account? Register'),
                  ),
                  const SizedBox(height: 20),
                  const Text(disclaimer, style: TextStyle(color: Color(0xff98a2b3), height: 1.35)),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class HomeShell extends StatefulWidget {
  const HomeShell({super.key, required this.api, required this.user, required this.onLogout});
  final ApiClient api;
  final Map<String, dynamic> user;
  final VoidCallback onLogout;

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int index = 0;
  int refreshTick = 0;

  void refresh() => setState(() => refreshTick++);

  @override
  Widget build(BuildContext context) {
    final pages = [
      DashboardPage(api: widget.api, refreshTick: refreshTick, onChanged: refresh),
      ZonesPage(api: widget.api),
      WeeklyPage(api: widget.api, refreshTick: refreshTick),
      SettingsPage(user: widget.user, api: widget.api, onLogout: widget.onLogout),
      const PrivacyPage(),
    ];
    return Scaffold(
      body: pages[index],
      bottomNavigationBar: NavigationBar(
        selectedIndex: index,
        onDestinationSelected: (value) => setState(() => index = value),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.dashboard_outlined), selectedIcon: Icon(Icons.dashboard), label: 'Home'),
          NavigationDestination(icon: Icon(Icons.map_outlined), selectedIcon: Icon(Icons.map), label: 'Zones'),
          NavigationDestination(icon: Icon(Icons.query_stats), label: 'Reports'),
          NavigationDestination(icon: Icon(Icons.settings_outlined), label: 'Settings'),
          NavigationDestination(icon: Icon(Icons.privacy_tip_outlined), label: 'Privacy'),
        ],
      ),
    );
  }
}

class DashboardPage extends StatefulWidget {
  const DashboardPage({super.key, required this.api, required this.refreshTick, required this.onChanged});
  final ApiClient api;
  final int refreshTick;
  final VoidCallback onChanged;

  @override
  State<DashboardPage> createState() => _DashboardPageState();
}

class _DashboardPageState extends State<DashboardPage> {
  List<dynamic> shifts = [];
  Map<String, dynamic>? activeVehicle;
  bool loading = true;
  bool shiftBusy = false;
  String? error;

  @override
  void initState() {
    super.initState();
    load();
  }

  @override
  void didUpdateWidget(covariant DashboardPage oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.refreshTick != widget.refreshTick) load();
  }

  Future<void> load() async {
    setState(() => loading = true);
    try {
      shifts = await widget.api.request('GET', '/shifts') as List<dynamic>;
      activeVehicle = await widget.api.request('GET', '/vehicles/active') as Map<String, dynamic>?;
      error = null;
    } catch (err) {
      error = err.toString();
    }
    if (mounted) setState(() => loading = false);
  }

  Map<String, dynamic>? get activeShift {
    for (final shift in shifts) {
      if (shift['ended_at'] == null) return shift as Map<String, dynamic>;
    }
    return null;
  }

  Future<void> startShift() async {
    setState(() {
      shiftBusy = true;
      error = null;
    });
    try {
      if (activeVehicle == null) {
        final vehicle = await Navigator.of(context).push<Map<String, dynamic>>(
          MaterialPageRoute(builder: (_) => VehicleSetupPage(api: widget.api)),
        );
        if (vehicle == null) return;
        setState(() => activeVehicle = vehicle);
      }
      if (!mounted) return;
      final platform = await showModalBottomSheet<String>(
        context: context,
        builder: (context) => PlatformPicker(),
      );
      if (platform == null) return;
      await widget.api.request('POST', '/shifts/start', body: {'platform': platform});
      await load();
      widget.onChanged();
    } catch (err) {
      if (mounted) {
        setState(() => error = err.toString().replaceFirst('Exception: ', ''));
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error ?? 'Could not start shift')));
      }
    } finally {
      if (mounted) setState(() => shiftBusy = false);
    }
  }

  Future<void> endShift(Map<String, dynamic> shift) async {
    final complete = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('End shift completely?'),
        content: const Text('Choose yes only when you are done for this shift. If you are just pausing, keep the shift open and use a break type instead.'),
        actions: [
          TextButton(onPressed: () => Navigator.of(context).pop(false), child: const Text('Not yet')),
          FilledButton(onPressed: () => Navigator.of(context).pop(true), child: const Text('Yes, final tally')),
        ],
      ),
    );
    if (complete != true) return;
    final result = await Navigator.of(context).push<Map<String, dynamic>>(
      MaterialPageRoute(builder: (_) => ShiftFormPage(api: widget.api, shift: shift, endMode: true)),
    );
    if (result != null) widget.onChanged();
  }

  @override
  Widget build(BuildContext context) {
    final active = activeShift;
    final today = shifts.where((shift) => isToday(DateTime.parse(shift['started_at'] as String))).toList();
    final grossToday = sumField(today, 'gross_earnings');
    final weekGross = sumField(shifts, 'gross_earnings');
    final weekMiles = sumField(shifts, 'miles');

    return Scaffold(
      appBar: AppBar(
        leading: const Padding(padding: EdgeInsets.all(8), child: LogoBadge()),
        title: const Text('GigOS'),
        actions: [IconButton(onPressed: load, icon: const Icon(Icons.refresh))],
      ),
      body: RefreshIndicator(
        onRefresh: load,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            if (error != null) Text(error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
            AnimatedSwitcher(
              duration: const Duration(milliseconds: 280),
              child: FilledButton.icon(
                key: ValueKey(active == null ? 'off' : 'on'),
                onPressed: shiftBusy ? null : active == null ? startShift : () => endShift(active),
                icon: Icon(active == null ? Icons.play_arrow : Icons.stop),
                style: FilledButton.styleFrom(
                  minimumSize: const Size.fromHeight(64),
                  backgroundColor: active == null ? const Color(0xff32d583) : const Color(0xfff97066),
                  foregroundColor: const Color(0xff101418),
                ),
                label: Text(shiftBusy ? 'Starting...' : active == null ? 'Start Shift' : 'Clock Out', style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w800)),
              ),
            ),
            const SizedBox(height: 16),
            if (active != null) ActiveShiftCard(api: widget.api, shift: active, onChanged: widget.onChanged),
            if (activeVehicle == null) ...[
              const SizedBox(height: 16),
              SetupPromptCard(
                onTap: () async {
                  final vehicle = await Navigator.of(context).push<Map<String, dynamic>>(
                    MaterialPageRoute(builder: (_) => VehicleSetupPage(api: widget.api)),
                  );
                  if (vehicle != null) setState(() => activeVehicle = vehicle);
                },
              ),
            ],
            const SizedBox(height: 16),
            Wrap(
              spacing: 12,
              runSpacing: 12,
              children: [
                MetricCard(label: 'Today', value: money(grossToday), icon: Icons.today),
                MetricCard(label: 'This Week', value: money(weekGross), icon: Icons.calendar_month),
                MetricCard(label: 'Net Hourly', value: active == null ? '\$0.00' : money(active['metrics']['net_hourly']), icon: Icons.payments_outlined),
                MetricCard(label: 'Miles', value: weekMiles.toStringAsFixed(1), icon: Icons.route_outlined),
                MetricCard(label: 'Break Status', value: active == null ? 'Ready' : active['break_status']['level'], icon: Icons.coffee_outlined),
              ],
            ),
            const SizedBox(height: 18),
            Text('Recent Shifts', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 10),
            if (loading) const Center(child: Padding(padding: EdgeInsets.all(24), child: CircularProgressIndicator())),
            ...shifts.take(10).map((shift) => ShiftTile(api: widget.api, shift: shift as Map<String, dynamic>, onChanged: widget.onChanged)),
          ],
        ),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () async {
          final result = await Navigator.of(context).push(MaterialPageRoute(builder: (_) => ShiftFormPage(api: widget.api)));
          if (result != null) widget.onChanged();
        },
        child: const Icon(Icons.add),
      ),
    );
  }
}

class ActiveShiftCard extends StatelessWidget {
  const ActiveShiftCard({super.key, required this.api, required this.shift, required this.onChanged});
  final ApiClient api;
  final Map<String, dynamic> shift;
  final VoidCallback onChanged;

  Future<void> startBreak(BuildContext context, String breakType) async {
    try {
      final summary = await showDialog<Map<String, dynamic>>(
        context: context,
        builder: (_) => ShiftSummaryDialog(shift: shift),
      );
      if (summary == null) return;
      await api.request('PATCH', '/shifts/${shift['id']}', body: summary);
      if (!context.mounted) return;
      final shiftForBreak = Map<String, dynamic>.from(shift);
      shiftForBreak.addAll(summary);
      final result = await Navigator.of(context).push(
        MaterialPageRoute(builder: (_) => BreakGuidePage(api: api, shift: shiftForBreak, breakType: breakType)),
      );
      if (result != null) onChanged();
    } catch (err) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(err.toString().replaceFirst('Exception: ', ''))));
      }
    }
  }

  Future<void> endBreak(int id) async {
    await api.request('PATCH', '/breaks/$id/end', body: {});
    onChanged();
  }

  @override
  Widget build(BuildContext context) {
    final breaks = shift['breaks'] as List<dynamic>;
    final activeBreak = breaks.cast<Map<String, dynamic>?>().firstWhere((item) => item?['ended_at'] == null, orElse: () => null);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Active Shift', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            Text('${shift['platform']} - ${shift['metrics']['total_minutes']} minutes online'),
            const SizedBox(height: 10),
            Text(shift['break_status']['message'], style: const TextStyle(color: Color(0xfffdb022))),
            const SizedBox(height: 12),
            if (activeBreak == null)
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  OutlinedButton.icon(onPressed: () => startBreak(context, 'rest'), icon: const Icon(Icons.free_breakfast_outlined), label: const Text('Start Break')),
                  OutlinedButton.icon(onPressed: () => startBreak(context, 'lunch'), icon: const Icon(Icons.lunch_dining), label: const Text('Lunch')),
                  OutlinedButton.icon(onPressed: () => startBreak(context, 'emergency'), icon: const Icon(Icons.emergency_outlined), label: const Text('Emergency')),
                ],
              )
            else
              OutlinedButton.icon(
                onPressed: () => endBreak(activeBreak['id'] as int),
                icon: const Icon(Icons.timer_off_outlined),
                label: const Text('End Active Break'),
              ),
          ],
        ),
      ),
    );
  }
}

class ShiftFormPage extends StatefulWidget {
  const ShiftFormPage({super.key, required this.api, this.shift, this.endMode = false});
  final ApiClient api;
  final Map<String, dynamic>? shift;
  final bool endMode;

  @override
  State<ShiftFormPage> createState() => _ShiftFormPageState();
}

class _ShiftFormPageState extends State<ShiftFormPage> {
  final platforms = ['Uber Eats', 'DoorDash', 'Grubhub', 'Instacart', 'Amazon Flex', 'Other'];
  late String platform;
  late final TextEditingController gross;
  late final TextEditingController tips;
  late final TextEditingController trips;
  late final TextEditingController miles;
  late final TextEditingController gas;
  late final TextEditingController other;
  late final TextEditingController active;
  late final TextEditingController notes;
  bool busy = false;

  @override
  void initState() {
    super.initState();
    platform = widget.shift?['platform']?.toString() ?? 'Uber Eats';
    gross = controller('gross_earnings');
    tips = controller('tips');
    trips = controller('trips');
    miles = controller('miles');
    gas = controller('gas_cost');
    other = controller('other_expenses');
    active = controller('active_minutes');
    notes = TextEditingController(text: widget.shift?['notes']?.toString() ?? '');
  }

  TextEditingController controller(String field) => TextEditingController(text: widget.shift?[field]?.toString() ?? '0');

  @override
  void dispose() {
    gross.dispose();
    tips.dispose();
    trips.dispose();
    miles.dispose();
    gas.dispose();
    other.dispose();
    active.dispose();
    notes.dispose();
    super.dispose();
  }

  Future<void> save() async {
    setState(() => busy = true);
    final body = {
      'platform': platform,
      'gross_earnings': parse(gross.text),
      'tips': parse(tips.text),
      'trips': int.tryParse(trips.text) ?? 0,
      'miles': parse(miles.text),
      'gas_cost': parse(gas.text),
      'other_expenses': parse(other.text),
      'active_minutes': int.tryParse(active.text) ?? 0,
      'notes': notes.text,
    };
    if (widget.shift == null) {
      body['started_at'] = DateTime.now().subtract(const Duration(hours: 1)).toUtc().toIso8601String();
      body['ended_at'] = DateTime.now().toUtc().toIso8601String();
      await widget.api.request('POST', '/shifts', body: body);
    } else {
      final path = widget.endMode ? '/shifts/${widget.shift!['id']}/end' : '/shifts/${widget.shift!['id']}';
      await widget.api.request('PATCH', path, body: body);
    }
    if (mounted) Navigator.of(context).pop(body);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.endMode ? 'End Shift' : widget.shift == null ? 'Add Shift' : 'Edit Shift')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          if (widget.endMode && widget.shift != null) FinalTallyCard(shift: widget.shift!),
          if (widget.endMode) const SizedBox(height: 12),
          DropdownButtonFormField<String>(
            value: platform,
            items: platforms.map((item) => DropdownMenuItem(value: item, child: Text(item))).toList(),
            onChanged: (value) => setState(() => platform = value ?? platform),
            decoration: const InputDecoration(labelText: 'Platform'),
          ),
          Field(controller: gross, label: 'Gross earnings', icon: Icons.attach_money),
          Field(controller: tips, label: 'Tips', icon: Icons.volunteer_activism_outlined),
          Field(controller: trips, label: 'Trips completed', icon: Icons.local_shipping_outlined),
          Field(controller: miles, label: 'Miles driven', icon: Icons.route_outlined),
          Field(controller: gas, label: 'Gas cost', icon: Icons.local_gas_station_outlined),
          Field(controller: other, label: 'Other expenses', icon: Icons.receipt_long_outlined),
          Field(controller: active, label: 'Active minutes', icon: Icons.timer_outlined),
          const SizedBox(height: 12),
          TextField(controller: notes, maxLines: 3, decoration: const InputDecoration(labelText: 'Notes')),
          const SizedBox(height: 18),
          FilledButton(onPressed: busy ? null : save, style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(54)), child: Text(busy ? 'Saving...' : 'Save')),
        ],
      ),
    );
  }
}

class FinalTallyCard extends StatelessWidget {
  const FinalTallyCard({super.key, required this.shift});
  final Map<String, dynamic> shift;

  @override
  Widget build(BuildContext context) {
    final metrics = shift['metrics'] as Map<String, dynamic>;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Final tally preview', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            ReportRow('Gross', money(shift['gross_earnings'])),
            ReportRow('Trips', shift['trips'].toString()),
            ReportRow('Miles', parse(shift['miles']).toStringAsFixed(1)),
            ReportRow('Net hourly', money(metrics['net_hourly'])),
            ReportRow('Net profit', money(metrics['net_profit'])),
          ],
        ),
      ),
    );
  }
}

class ShiftSummaryDialog extends StatefulWidget {
  const ShiftSummaryDialog({super.key, required this.shift});
  final Map<String, dynamic> shift;

  @override
  State<ShiftSummaryDialog> createState() => _ShiftSummaryDialogState();
}

class _ShiftSummaryDialogState extends State<ShiftSummaryDialog> {
  late final TextEditingController gross;
  late final TextEditingController tips;
  late final TextEditingController trips;
  late final TextEditingController miles;
  late final TextEditingController active;

  @override
  void initState() {
    super.initState();
    gross = TextEditingController(text: widget.shift['gross_earnings']?.toString() ?? '0');
    tips = TextEditingController(text: widget.shift['tips']?.toString() ?? '0');
    trips = TextEditingController(text: widget.shift['trips']?.toString() ?? '0');
    miles = TextEditingController(text: widget.shift['miles']?.toString() ?? '0');
    active = TextEditingController(text: widget.shift['active_minutes']?.toString() ?? '0');
  }

  @override
  void dispose() {
    gross.dispose();
    tips.dispose();
    trips.dispose();
    miles.dispose();
    active.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text('${widget.shift['platform']} summary'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Field(controller: gross, label: 'Gross earnings so far', icon: Icons.attach_money),
            Field(controller: tips, label: 'Tips so far', icon: Icons.volunteer_activism_outlined),
            Field(controller: trips, label: 'Trips completed', icon: Icons.local_shipping_outlined),
            Field(controller: miles, label: 'Miles driven', icon: Icons.route_outlined),
            Field(controller: active, label: 'Active minutes', icon: Icons.timer_outlined),
          ],
        ),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text('Cancel')),
        FilledButton(
          onPressed: () => Navigator.of(context).pop({
            'platform': widget.shift['platform'],
            'gross_earnings': parse(gross.text),
            'tips': parse(tips.text),
            'trips': int.tryParse(trips.text) ?? 0,
            'miles': parse(miles.text),
            'active_minutes': int.tryParse(active.text) ?? 0,
          }),
          child: const Text('Continue'),
        ),
      ],
    );
  }
}

class BreakGuidePage extends StatefulWidget {
  const BreakGuidePage({super.key, required this.api, required this.shift, required this.breakType});
  final ApiClient api;
  final Map<String, dynamic> shift;
  final String breakType;

  @override
  State<BreakGuidePage> createState() => _BreakGuidePageState();
}

class _BreakGuidePageState extends State<BreakGuidePage> {
  GeoPoint? location;
  List<dynamic> zones = [];
  List<dynamic> hotspots = [];
  bool loading = true;
  String? error;

  @override
  void initState() {
    super.initState();
    load();
  }

  Future<void> load() async {
    setState(() {
      loading = true;
      error = null;
    });
    try {
      location = await currentLocation();
      final breakData = await widget.api.request('GET', '/locations/break-zones?lat=${location!.lat}&lon=${location!.lon}') as Map<String, dynamic>;
      final activityData = await widget.api.request('GET', '/locations/activity?lat=${location!.lat}&lon=${location!.lon}') as Map<String, dynamic>;
      zones = breakData['zones'] as List<dynamic>;
      hotspots = activityData['hotspots'] as List<dynamic>;
    } catch (err) {
      error = err.toString().replaceFirst('Exception: ', '');
    }
    if (mounted) setState(() => loading = false);
  }

  Future<void> confirmBreak(Map<String, dynamic> zone) async {
    try {
      final here = await currentLocation();
      await widget.api.request('POST', '/shifts/${widget.shift['id']}/breaks/start', body: {
        'break_type': widget.breakType,
        'location_name': zone['name'],
        'latitude': here.lat,
        'longitude': here.lon,
        'target_latitude': zone['latitude'],
        'target_longitude': zone['longitude'],
        'notes': 'Geo-confirmed break at ${zone['name']}',
      });
      if (mounted) Navigator.of(context).pop(true);
    } catch (err) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(err.toString().replaceFirst('Exception: ', ''))));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Break Zones')),
      body: loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                if (error != null) Text(error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
                if (location != null) DataMap(origin: location!, zones: zones, hotspots: hotspots),
                const SizedBox(height: 16),
                Text('Closest break locations', style: Theme.of(context).textTheme.titleLarge),
                const SizedBox(height: 10),
                ...zones.map((zone) => ZoneTile(zone: zone as Map<String, dynamic>, onConfirm: () => confirmBreak(zone))),
                if (zones.isEmpty) const Text('No 24-hour break locations found nearby. Try refreshing after moving closer to a commercial area.'),
                const SizedBox(height: 16),
                Text('Hot zone places', style: Theme.of(context).textTheme.titleLarge),
                const SizedBox(height: 10),
                ...hotspots.map((hotspot) => HotspotTile(hotspot: hotspot as Map<String, dynamic>)),
              ],
            ),
    );
  }
}

class ZonesPage extends StatefulWidget {
  const ZonesPage({super.key, required this.api});
  final ApiClient api;

  @override
  State<ZonesPage> createState() => _ZonesPageState();
}

class _ZonesPageState extends State<ZonesPage> {
  GeoPoint? location;
  List<dynamic> zones = [];
  List<dynamic> hotspots = [];
  bool loading = false;
  String? error;

  @override
  void initState() {
    super.initState();
    load();
  }

  Future<void> load() async {
    setState(() {
      loading = true;
      error = null;
    });
    try {
      location = await currentLocation();
      final breakData = await widget.api.request('GET', '/locations/break-zones?lat=${location!.lat}&lon=${location!.lon}') as Map<String, dynamic>;
      final activityData = await widget.api.request('GET', '/locations/activity?lat=${location!.lat}&lon=${location!.lon}') as Map<String, dynamic>;
      zones = breakData['zones'] as List<dynamic>;
      hotspots = activityData['hotspots'] as List<dynamic>;
    } catch (err) {
      error = err.toString().replaceFirst('Exception: ', '');
    }
    if (mounted) setState(() => loading = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Hot Zones')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          FilledButton.icon(
            onPressed: loading ? null : load,
            icon: const Icon(Icons.my_location),
            label: Text(loading ? 'Locating...' : 'Use My Location'),
          ),
          const SizedBox(height: 12),
          const Text('Activity is estimated from public restaurant, cafe, convenience, and retail POI density. It is not Uber or delivery-platform order data.', style: TextStyle(color: Color(0xff98a2b3), height: 1.35)),
          const SizedBox(height: 16),
          if (error != null) Text(error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
          if (location != null) DataMap(origin: location!, zones: zones, hotspots: hotspots),
          const SizedBox(height: 16),
          Text('24-hour break spots', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 10),
          ...zones.map((zone) => ZoneTile(zone: zone as Map<String, dynamic>, onConfirm: null)),
          const SizedBox(height: 16),
          Text('Hot zone places', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 10),
          ...hotspots.map((hotspot) => HotspotTile(hotspot: hotspot as Map<String, dynamic>)),
        ],
      ),
    );
  }
}

class DataMap extends StatelessWidget {
  const DataMap({super.key, required this.origin, required this.zones, required this.hotspots});
  final GeoPoint origin;
  final List<dynamic> zones;
  final List<dynamic> hotspots;

  @override
  Widget build(BuildContext context) {
    return AspectRatio(
      aspectRatio: 1.25,
      child: Card(
        child: LayoutBuilder(
          builder: (context, constraints) {
            return Stack(
              clipBehavior: Clip.hardEdge,
              children: [
                Positioned.fill(child: CustomPaint(painter: MapGridPainter())),
                const Center(child: Icon(Icons.navigation, color: Colors.white, size: 30)),
                ...hotspots.take(10).map((item) => _mapDot(
                      constraints: constraints,
                      item: item as Map<String, dynamic>,
                      color: const Color(0x99fdb022),
                      size: (18 + parse(item['score']).clamp(0, 16)).toDouble(),
                    )),
                ...zones.take(8).map((item) => _mapDot(
                      constraints: constraints,
                      item: item as Map<String, dynamic>,
                      color: const Color(0xff32d583),
                      size: 14,
                    )),
                const Positioned(left: 12, bottom: 12, child: Text('Open POI heat map', style: TextStyle(color: Color(0xff98a2b3)))),
              ],
            );
          },
        ),
      ),
    );
  }

  Widget _mapDot({
    required BoxConstraints constraints,
    required Map<String, dynamic> item,
    required Color color,
    required double size,
  }) {
    final width = constraints.maxWidth;
    final height = constraints.maxHeight;
    final latDelta = (parse(item['latitude']) - origin.lat).clamp(-0.025, 0.025).toDouble();
    final lonDelta = (parse(item['longitude']) - origin.lon).clamp(-0.025, 0.025).toDouble();
    final x = 0.5 + lonDelta / 0.05;
    final y = 0.5 - latDelta / 0.05;
    return Positioned(
      left: (x * width - size / 2).clamp(6.0, width - size - 6).toDouble(),
      top: (y * height - size / 2).clamp(6.0, height - size - 6).toDouble(),
      child: Tooltip(
        message: item['name']?.toString() ?? item['label']?.toString() ?? 'Map point',
        child: Container(width: size, height: size, decoration: BoxDecoration(color: color, shape: BoxShape.circle)),
      ),
    );
  }
}

class MapGridPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = const Color(0xff26313a)
      ..strokeWidth = 1;
    for (var i = 1; i < 5; i++) {
      canvas.drawLine(Offset(size.width * i / 5, 0), Offset(size.width * i / 5, size.height), paint);
      canvas.drawLine(Offset(0, size.height * i / 5), Offset(size.width, size.height * i / 5), paint);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

class ZoneTile extends StatelessWidget {
  const ZoneTile({super.key, required this.zone, required this.onConfirm});
  final Map<String, dynamic> zone;
  final VoidCallback? onConfirm;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: ListTile(
        leading: Icon(zone['open_24_7'] == true ? Icons.local_gas_station : Icons.place_outlined, color: const Color(0xff32d583)),
        title: Text(zone['name']?.toString() ?? 'Break location'),
        subtitle: Text('${zone['distance_miles']} mi - ${zone['kind']} ${zone['open_24_7'] == true ? '- 24/7' : ''}'),
        trailing: onConfirm == null ? const Icon(Icons.chevron_right) : FilledButton(onPressed: onConfirm, child: const Text("I'm here")),
        onTap: () => html.window.open('https://www.openstreetmap.org/?mlat=${zone['latitude']}&mlon=${zone['longitude']}#map=17/${zone['latitude']}/${zone['longitude']}', '_blank'),
      ),
    );
  }
}

class HotspotTile extends StatelessWidget {
  const HotspotTile({super.key, required this.hotspot});
  final Map<String, dynamic> hotspot;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: ListTile(
        leading: const Icon(Icons.local_fire_department_outlined, color: Color(0xfffdb022)),
        title: Text(hotspot['label']?.toString() ?? 'Activity cluster'),
        subtitle: Text('${hotspot['distance_miles']} mi - density score ${hotspot['score']}'),
      ),
    );
  }
}

class GeoPoint {
  GeoPoint(this.lat, this.lon);
  final double lat;
  final double lon;
}

Future<GeoPoint> currentLocation() async {
  final position = await html.window.navigator.geolocation.getCurrentPosition(enableHighAccuracy: true);
  final latitude = position.coords?.latitude;
  final longitude = position.coords?.longitude;
  if (latitude == null || longitude == null) {
    throw Exception('Location unavailable');
  }
  return GeoPoint(latitude.toDouble(), longitude.toDouble());
}

class WeeklyPage extends StatefulWidget {
  const WeeklyPage({super.key, required this.api, required this.refreshTick});
  final ApiClient api;
  final int refreshTick;

  @override
  State<WeeklyPage> createState() => _WeeklyPageState();
}

class _WeeklyPageState extends State<WeeklyPage> {
  Map<String, dynamic>? report;

  @override
  void initState() {
    super.initState();
    load();
  }

  Future<void> load() async {
    report = await widget.api.request('GET', '/reports/weekly') as Map<String, dynamic>;
    if (mounted) setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    final data = report;
    return Scaffold(
      appBar: AppBar(title: const Text('Weekly Reports')),
      body: data == null
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  children: [
                    MetricCard(label: 'Gross', value: money(data['gross_earnings']), icon: Icons.trending_up),
                    MetricCard(label: 'Net Hourly', value: money(data['net_hourly']), icon: Icons.payments_outlined),
                    MetricCard(label: 'Miles', value: parse(data['miles']).toStringAsFixed(1), icon: Icons.route_outlined),
                    MetricCard(label: 'Tax Set Aside', value: money(data['tax_set_aside']), icon: Icons.account_balance_outlined),
                  ],
                ),
                const SizedBox(height: 16),
                ReportRow('Shifts', data['shifts'].toString()),
                ReportRow('Online hours', (data['online_minutes'] / 60).toStringAsFixed(1)),
                ReportRow('Active hours', (data['active_minutes'] / 60).toStringAsFixed(1)),
                ReportRow('Trips', data['trips'].toString()),
                ReportRow('Maintenance reserve', money(data['maintenance_reserve'])),
                ReportRow('Net profit', money(data['net_profit'])),
                const SizedBox(height: 18),
                OutlinedButton.icon(
                  onPressed: () => downloadCsv(context),
                  icon: const Icon(Icons.download_outlined),
                  label: const Text('Export CSV'),
                ),
              ],
            ),
    );
  }

  Future<void> downloadCsv(BuildContext context) async {
    final response = await http.get(Uri.parse('$apiBaseUrl/export/csv'), headers: widget.api.headers);
    if (response.statusCode >= 400) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('CSV export failed')));
      }
      return;
    }
    final blob = html.Blob([response.body], 'text/csv');
    final url = html.Url.createObjectUrlFromBlob(blob);
    html.AnchorElement(href: url)
      ..download = 'gigos-shifts.csv'
      ..click();
    html.Url.revokeObjectUrl(url);
  }
}

class SettingsPage extends StatelessWidget {
  const SettingsPage({super.key, required this.user, required this.onLogout, required this.api});
  final Map<String, dynamic> user;
  final VoidCallback onLogout;
  final ApiClient api;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: ListTile(
              leading: const Icon(Icons.person_outline),
              title: Text(user['email'] as String),
              subtitle: const Text('Local GigOS account'),
            ),
          ),
          const SizedBox(height: 12),
          Card(
            child: ListTile(
              leading: const Icon(Icons.directions_car_outlined),
              title: const Text('Vehicle profile'),
              subtitle: const Text('Pick one active vehicle for MPG and gas-cost estimates.'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => VehicleSetupPage(api: api))),
            ),
          ),
          const SizedBox(height: 12),
          Card(
            child: const ListTile(
              leading: Icon(Icons.lock_outline),
              title: Text('Privacy first'),
              subtitle: Text('GigOS never stores delivery platform passwords and does not scrape or use third-party gig platform APIs.'),
            ),
          ),
          const SizedBox(height: 18),
          OutlinedButton.icon(onPressed: onLogout, icon: const Icon(Icons.logout), label: const Text('Logout')),
        ],
      ),
    );
  }
}

class VehicleSetupPage extends StatefulWidget {
  const VehicleSetupPage({super.key, required this.api});
  final ApiClient api;

  @override
  State<VehicleSetupPage> createState() => _VehicleSetupPageState();
}

class _VehicleSetupPageState extends State<VehicleSetupPage> {
  List<dynamic> catalog = [];
  List<dynamic> vehicles = [];
  Map<String, dynamic>? selected;
  final fuelPrice = TextEditingController(text: '3.50');
  bool loading = true;
  bool saving = false;
  String? error;

  @override
  void initState() {
    super.initState();
    load();
  }

  @override
  void dispose() {
    fuelPrice.dispose();
    super.dispose();
  }

  Future<void> load() async {
    try {
      catalog = await widget.api.request('GET', '/vehicles/catalog') as List<dynamic>;
      vehicles = await widget.api.request('GET', '/vehicles') as List<dynamic>;
      selected = catalog.isNotEmpty ? catalog.first as Map<String, dynamic> : null;
      error = null;
    } catch (err) {
      error = err.toString().replaceFirst('Exception: ', '');
    }
    if (mounted) setState(() => loading = false);
  }

  Future<void> saveVehicle() async {
    if (selected == null) return;
    setState(() {
      saving = true;
      error = null;
    });
    try {
      final vehicle = await widget.api.request('POST', '/vehicles', body: {
        'catalog_id': selected!['id'],
        'nickname': '${selected!['make']} ${selected!['model']}',
        'fuel_price_per_gallon': parse(fuelPrice.text),
        'is_active': true,
      }) as Map<String, dynamic>;
      if (mounted) Navigator.of(context).pop(vehicle);
    } catch (err) {
      if (mounted) {
        setState(() => error = err.toString().replaceFirst('Exception: ', ''));
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error ?? 'Could not save vehicle')));
      }
    } finally {
      if (mounted) setState(() => saving = false);
    }
  }

  Future<void> setVehicleActive(Map<String, dynamic> vehicle) async {
    try {
      final active = await widget.api.request('PATCH', '/vehicles/${vehicle['id']}/active') as Map<String, dynamic>;
      if (mounted) Navigator.of(context).pop(active);
    } catch (err) {
      if (mounted) setState(() => error = err.toString().replaceFirst('Exception: ', ''));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Vehicle Profile')),
      body: loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                if (error != null) Text(error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
                Text('Active vehicle', style: Theme.of(context).textTheme.titleLarge),
                const SizedBox(height: 8),
                if (vehicles.isEmpty) const Text('Add your vehicle before going on shift so GigOS can estimate fuel cost from MPG.'),
                ...vehicles.map((item) {
                  final vehicle = item as Map<String, dynamic>;
                  return Card(
                    margin: const EdgeInsets.only(bottom: 10),
                    child: ListTile(
                      leading: Icon(vehicle['is_active'] == true ? Icons.check_circle : Icons.radio_button_unchecked, color: const Color(0xff32d583)),
                      title: Text('${vehicle['year']} ${vehicle['make']} ${vehicle['model']}'),
                      subtitle: Text('${vehicle['mpg_combined']} MPG combined - \$${vehicle['fuel_price_per_gallon']}/gal'),
                      trailing: vehicle['is_active'] == true ? const Text('Active') : TextButton(onPressed: () => setVehicleActive(vehicle), child: const Text('Use')),
                    ),
                  );
                }),
                const SizedBox(height: 18),
                Text('Add common vehicle', style: Theme.of(context).textTheme.titleLarge),
                const SizedBox(height: 10),
                DropdownButtonFormField<Map<String, dynamic>>(
                  value: selected,
                  items: catalog.map((item) {
                    final car = item as Map<String, dynamic>;
                    return DropdownMenuItem<Map<String, dynamic>>(
                      value: car,
                      child: Text('${car['year']} ${car['make']} ${car['model']} - ${car['mpg_combined']} MPG'),
                    );
                  }).toList(),
                  onChanged: (value) => setState(() => selected = value),
                  decoration: const InputDecoration(labelText: 'Vehicle'),
                ),
                const SizedBox(height: 12),
                TextField(controller: fuelPrice, keyboardType: const TextInputType.numberWithOptions(decimal: true), decoration: const InputDecoration(labelText: 'Fuel price per gallon')),
                const SizedBox(height: 18),
                FilledButton.icon(
                  onPressed: saving ? null : saveVehicle,
                  icon: const Icon(Icons.directions_car),
                  label: Text(saving ? 'Saving...' : 'Save as Active Vehicle'),
                ),
              ],
            ),
    );
  }
}

class SetupPromptCard extends StatelessWidget {
  const SetupPromptCard({super.key, required this.onTap});
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ListTile(
        leading: const Icon(Icons.directions_car, color: Color(0xff32d583)),
        title: const Text('Add your vehicle'),
        subtitle: const Text('Set MPG once so shifts can estimate fuel cost automatically.'),
        trailing: const Icon(Icons.chevron_right),
        onTap: onTap,
      ),
    );
  }
}

class PrivacyPage extends StatelessWidget {
  const PrivacyPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Privacy')),
      body: const Padding(
        padding: EdgeInsets.all(16),
        child: Card(
          child: Padding(
            padding: EdgeInsets.all(16),
            child: Text('$disclaimer\n\nNo scraping. No third-party gig platform API usage. Never store platform passwords.', style: TextStyle(height: 1.45)),
          ),
        ),
      ),
    );
  }
}

class MetricCard extends StatelessWidget {
  const MetricCard({super.key, required this.label, required this.value, required this.icon});
  final String label;
  final String value;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: MediaQuery.of(context).size.width >= 520 ? 160 : (MediaQuery.of(context).size.width - 44) / 2,
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Center(child: Icon(icon, color: const Color(0xff32d583))),
              const SizedBox(height: 12),
              Text(value, textAlign: TextAlign.center, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w800)),
              const SizedBox(height: 3),
              Text(label, textAlign: TextAlign.center, style: const TextStyle(color: Color(0xff98a2b3))),
            ],
          ),
        ),
      ),
    );
  }
}

class ShiftTile extends StatelessWidget {
  const ShiftTile({super.key, required this.api, required this.shift, required this.onChanged});
  final ApiClient api;
  final Map<String, dynamic> shift;
  final VoidCallback onChanged;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: ListTile(
        title: Text('${shift['platform']} · ${money(shift['gross_earnings'])}'),
        subtitle: Text('${DateFormat.MMMd().add_jm().format(DateTime.parse(shift['started_at'] as String).toLocal())} · ${shift['metrics']['total_minutes']} min'),
        trailing: const Icon(Icons.chevron_right),
        onTap: () async {
          final result = await Navigator.of(context).push(MaterialPageRoute(builder: (_) => ShiftFormPage(api: api, shift: shift)));
          if (result != null) onChanged();
        },
      ),
    );
  }
}

class Field extends StatelessWidget {
  const Field({super.key, required this.controller, required this.label, required this.icon});
  final TextEditingController controller;
  final String label;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: TextField(
        controller: controller,
        keyboardType: const TextInputType.numberWithOptions(decimal: true),
        decoration: InputDecoration(labelText: label, prefixIcon: Icon(icon)),
      ),
    );
  }
}

class ReportRow extends StatelessWidget {
  const ReportRow(this.label, this.value, {super.key});
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      contentPadding: EdgeInsets.zero,
      title: Text(label),
      trailing: Text(value, style: const TextStyle(fontWeight: FontWeight.w700)),
    );
  }
}

class PlatformPicker extends StatelessWidget {
  PlatformPicker({super.key});
  final platforms = ['Uber Eats', 'DoorDash', 'Grubhub', 'Instacart', 'Amazon Flex', 'Other'];

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: ListView(
        shrinkWrap: true,
        children: [
          const ListTile(title: Text('Choose platform')),
          ...platforms.map((platform) => ListTile(title: Text(platform), onTap: () => Navigator.of(context).pop(platform))),
        ],
      ),
    );
  }
}

bool isToday(DateTime date) {
  final now = DateTime.now();
  final local = date.toLocal();
  return local.year == now.year && local.month == now.month && local.day == now.day;
}

double parse(dynamic value) => double.tryParse(value.toString()) ?? 0;

double sumField(List<dynamic> items, String field) => items.fold(0, (sum, item) => sum + parse(item[field]));

String money(dynamic value) => NumberFormat.simpleCurrency().format(parse(value));
