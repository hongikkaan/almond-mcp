const {createHash} = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const {parseArgs} = require('node:util');

const ROOT = path.resolve(__dirname, '..', '..');
const SOURCE = path.join(ROOT, 'TOOL-DECLARATIONS-CURRENT.md');
const TARGET = path.join(ROOT, 'src', 'mcp', 'public_contract_data.json');
const TS_IN_VSCODE = path.join('resources', 'app', 'extensions', 'node_modules',
                               'typescript', 'lib', 'typescript.js');
const {values: options} = parseArgs({
  options: {check: {type: 'boolean'}, typescript: {type: 'string'}},
});
const ts = loadTypeScript(options.typescript ?? process.env.ALMOND_TYPESCRIPT_PATH);

const K = ts.SyntaxKind;
const kindToType = {
  [K.StringKeyword]: 'string', [K.NumberKeyword]: 'number', [K.BooleanKeyword]: 'boolean',
};
const aliases = new Map();
const commentAt = new Map();
const dedupe = values => [...new Set(values)];
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);

function loadTypeScript(explicit) {
  if (explicit) {
    const resolved = path.resolve(explicit);
    if (!fs.existsSync(resolved)) {
      throw Error(`TypeScript path does not exist: ${resolved}`);
    }
    return require(resolved);
  }
  try {
    return require('typescript');
  } catch (error) {
    if (error.code !== 'MODULE_NOT_FOUND') { throw error; }
  }
  const installations = [
    process.env.LOCALAPPDATA && path.join(process.env.LOCALAPPDATA, 'Programs', 'Microsoft VS Code'),
    process.env.ProgramFiles && path.join(process.env.ProgramFiles, 'Microsoft VS Code'),
    '/usr/share/code',
    '/Applications/Visual Studio Code.app/Contents',
  ];
  for (const dir of installations.filter(Boolean)) {
    if (!fs.existsSync(dir)) { continue; }

    const nested = fs.readdirSync(dir, {withFileTypes: true})
      .filter(entry => entry.isDirectory() && /^[0-9a-f]{10}$/i.test(entry.name))
      .map(entry => path.join(dir, entry.name));
    const modulePath = [dir, ...nested].map(root => path.join(root, TS_IN_VSCODE)).find(fs.existsSync);
    if (modulePath) { return require(modulePath); }
  }
  throw Error('TypeScript is required to compile tool declarations. Pass --typescript with the path to a local typescript.js.');
}

function union(schemas) {
  const flat = schemas.flatMap(s => Object.keys(s).length === 1 && s.anyOf ? s.anyOf : [s]);
  if (flat.every(s => Object.keys(s).length === 2 && 'const' in s && s.type === flat[0].type)) {
    return {type: flat[0].type, enum: dedupe(flat.map(s => s.const))};
  }
  const unique = flat.filter((s, i) => flat.findIndex(t => same(s, t)) === i);
  return unique.length === 1 ? unique[0] : {anyOf: unique};
}

function describe(node) {
  const source = node.getSourceFile();
  const text = source.text;
  const before = ts.getLeadingCommentRanges(text, node.pos) || [];
  const after = ts.getTrailingCommentRanges(text, node.end) || [];
  const all = [...before, ...after];
  if (!all.length) { return undefined; }
  for (const {pos} of all) commentAt.get(source.fileName).add(pos);
  return all.map(({pos, end}) => text.slice(pos, end)
    .replace(/^\/\/\s?/, '')
    .replace(/^\/\*+|\*\/$/g, '')
    .replace(/^\s*\*\s?/gm, '')
    .trim()).join('\n');
}

function inputDefault(schema) {
  // A literal default is valid metadata. Text such as "current model" stays prose.
  const match = schema.description?.match(/(?:^|·\s*)기본값\s+("(?:[^"\\]|\\.)*"|true|false|null|-?\d+(?:\.\d+)?)(?=\s|\.|$)/m);
  if (match) { return {...schema, default: JSON.parse(match[1])}; }
  return schema;
}

function literal(value) {
  if (value === null) { return {type: 'null'}; }
  return {type: typeof value, const: value};
}

function values(s) {
  if ('const' in s) { return [s.const]; }
  if ('enum' in s) { return s.enum; }
  if ('anyOf' in s) { return s.anyOf.flatMap(values); }
  throw Error(`Not a finite key set: ${JSON.stringify(s)}`);
}

function intersect(schemas) {
  if (schemas.length === 1) { return schemas[0]; }
  const choices = schemas.findIndex(s => Object.keys(s).length === 1 && s.anyOf);
  if (choices >= 0) { return union(schemas[choices].anyOf.map(branch =>
    intersect([...schemas.slice(0, choices), branch, ...schemas.slice(choices + 1)]))); }
  if (!schemas.every(s => s.type === 'object' && s.properties)) { return {allOf: schemas}; }
  const properties = {};
  for (const s of schemas) {
    for (const [key, value] of Object.entries(s.properties)) {
      properties[key] = key in properties && !same(properties[key], value)
        ? {allOf: [properties[key], value]} : value;
    }
  }
  const required = dedupe(schemas.flatMap(s => s.required ?? []));
  return object(properties, required, schemas.some(s => s.additionalProperties === false));
}

function object(properties, required, closed = false) {
  return {type: 'object', properties, ...(required.length && {required}),
          ...(closed && {additionalProperties: false})};
}

function record(key, val) {
  if (same(key, {type: 'string'})) {
    return val === false ? object({}, [], true)
         : {type: 'object', additionalProperties: Object.keys(val).length ? val : true};
  }
  const keys = values(key);
  if (keys.some(key => typeof key !== 'string')) {
    throw Error('Record keys in a tool declaration must be strings.');
  }
  return object(Object.fromEntries(keys.map(k => [k, val])), keys, true);
}

function reference(node, input, locals) {
  const name = node.typeName.getText();
  const parameters = [...node.typeArguments ?? []].map(arg => convert(arg, input, locals));
  const argumentCount = {Integer: 0, Array: 1, Record: 2, Partial: 1, Omit: 2, Pick: 2};
  const alias = aliases.get(name);
  const expected = argumentCount[name] ?? alias?.typeParameters?.length ?? 0;
  if (parameters.length !== expected) {
    throw Error(`${name} expects ${expected} type arguments.`);
  }
  if (name === 'Integer') { return {type: 'integer'}; }
  if (name === 'Array') { return {type: 'array', items: parameters[0]}; }
  if (name === 'Record') { return record(...parameters); }
  if (name === 'Partial') {
    const {required, ...result} = parameters[0];
    return result;
  }
  if (name === 'Omit' || name === 'Pick') {
    const [source, set] = parameters;
    const names = values(set);
    const keep = key => names.includes(key) === (name === 'Pick');
    return object(Object.fromEntries(Object.entries(source.properties).filter(([k]) => keep(k))),
                  (source.required ?? []).filter(keep), source.additionalProperties === false);
  }
  if (locals.has(name)) { return locals.get(name); }
  if (!alias) { throw Error(`Unknown alias ${name}`); }
  const scope = new Map(locals);
  for (const [i, param] of [...alias.typeParameters ?? []].entries()) {
    scope.set(param.name.text, parameters[i]);
  }
  const schema = convert(alias.type, input, scope);
  const description = describe(alias);
  return description ? {...schema, description} : schema;
}

function convert(node, input, locals = new Map()) {
  if (node.kind in kindToType) { return {type: kindToType[node.kind]}; }
  if (node.kind === K.UnknownKeyword) { return {}; }
  if (node.kind === K.NeverKeyword) { return false; }
  if (ts.isTypeLiteralNode(node)) {
    const properties = {};
    const required = [];
    for (const member of node.members) {
      if (!ts.isPropertySignature(member) || !member.type) { throw Error(member.getText()); }
      const key = member.name.text;
      const schema = convert(member.type, input, locals);
      const description = describe(member);
      if (schema === false && member.questionToken && input) { continue; }
      const annotated = schema === false ? {not: {}} : schema;
      properties[key] = description
        ? {...annotated, description: [description, schema.description].filter(Boolean).join('\n')}
        : schema;
      if (input) { properties[key] = inputDefault(properties[key]); }
      if (!member.questionToken) { required.push(key); }
    }
    return object(properties, required, input);
  }
  if (ts.isUnionTypeNode(node)) { return union(node.types.map(child => convert(child, input, locals))); }
  if (ts.isIntersectionTypeNode(node)) { return intersect(node.types.map(child => convert(child, input, locals))); }
  if (ts.isParenthesizedTypeNode(node)) { return convert(node.type, input, locals); }
  if (ts.isArrayTypeNode(node)) { return {type: 'array', items: convert(node.elementType, input, locals)}; }
  if (ts.isTupleTypeNode(node)) {
    const elements = node.elements.map(element => convert(element, input, locals));
    const length = elements.length;
    return {type: 'array', minItems: length, maxItems: length,
            ...(elements.every(element => same(element, elements[0]))
                 ? {items: elements[0]} : {prefixItems: elements})};
  }
  if (ts.isTypeReferenceNode(node)) { return reference(node, input, locals); }
  if (ts.isLiteralTypeNode(node)) {
    const v = node.literal;
    if (ts.isStringLiteral(v)) { return literal(v.text); }
    if (ts.isNumericLiteral(v)) { return literal(Number(v.text)); }
    if (v.kind === K.TrueKeyword) { return literal(true); }
    if (v.kind === K.FalseKeyword) { return literal(false); }
    if (v.kind === K.NullKeyword) { return literal(null); }
  }
  throw Error(`Unknown type ${ts.SyntaxKind[node.kind]}: ${node.getText()}`);
}

function root(schema, input) {
  if (schema.type === 'object') { return schema; }
  if (!schema.anyOf || !schema.anyOf.every(s => s.type === 'object')) {
    throw Error(`Expected object or union of objects: ${JSON.stringify(schema)}`);
  }
  const properties = {};
  const branches = schema.anyOf;
  for (const key of dedupe(branches.flatMap(s => Object.keys(s.properties)))) {
    const variants = branches.filter(s => key in s.properties).map(s => s.properties[key]);
    properties[key] = union(variants);
  }
  const required = (branches[0].required ?? []).filter(key => branches.every(s => s.required?.includes(key)));
  if (!input) { return {...object(properties, required), anyOf: branches}; }
  const variants = branches.map(s => ({
    properties: Object.fromEntries(Object.entries(properties).flatMap(([key, value]) => {
      if (!(key in s.properties)) { return [[key, false]]; }
      return same(value, s.properties[key]) ? [] : [[key, s.properties[key]]];
    })),
    ...((s.required ?? []).some(key => !required.includes(key)) && {
      required: s.required.filter(key => !required.includes(key)),
    }),
  }));
  return {...object(properties, required, true), anyOf: variants};
}

function readDeclaration([, name, description, code]) {
  const source = ts.createSourceFile(name, code, ts.ScriptTarget.Latest, true);
  if (source.parseDiagnostics.length) {
    throw Error(name + ': ' + source.parseDiagnostics.map(d => d.messageText).join(', '));
  }
  commentAt.set(name, new Set());
  for (const statement of source.statements) {
    if (ts.isTypeAliasDeclaration(statement)) {
      if (aliases.has(statement.name.text)) { throw Error(`Duplicate alias ${statement.name.text}`); }
      aliases.set(statement.name.text, statement);
    }
  }
  const variables = source.statements.filter(s => ts.isVariableStatement(s));
  const declaration = variables[0]?.declarationList.declarations[0];
  if (variables.length !== 1 || variables[0].declarationList.declarations.length !== 1 ||
      declaration.name.text !== 'tools' || !declaration.type || !ts.isTypeLiteralNode(declaration.type)) {
    throw Error(`Expected one tools declaration for ${name}.`);
  }
  const methods = declaration.type.members;
  if (methods.length !== 1 || !ts.isMethodSignature(methods[0]) ||
      methods[0].name.text !== `mcp__rhino__${name.replace('-', '_')}`) {
    throw Error(`Unexpected tool method for ${name}.`);
  }
  const method = methods[0];
  if (method.parameters.length !== 1 || method.parameters[0].name.text !== 'args' ||
      !method.parameters[0].type || !method.type || !ts.isTypeReferenceNode(method.type) ||
      method.type.typeName.text !== 'Promise' || method.type.typeArguments?.length !== 1) {
    throw Error(`Expected one input and a Promise return type for ${name}.`);
  }
  const result = method.type.typeArguments[0];
  if (!ts.isTypeReferenceNode(result) || result.typeArguments?.length !== 1 ||
      !['JsonResult', 'CallToolResult'].includes(result.typeName.text)) {
    throw Error(`Expected JsonResult or CallToolResult for ${name}.`);
  }
  const wrapped = result.typeName.text === 'JsonResult';
  return {name, description, code, wrapped, input: method.parameters[0].type, output: result.typeArguments[0]};
}

function checkComments({name, code}) {
  const scanner = ts.createScanner(ts.ScriptTarget.Latest, false, ts.LanguageVariant.Standard, code);
  for (let token = scanner.scan(); token !== K.EndOfFileToken; token = scanner.scan()) {
    if (token !== K.SingleLineCommentTrivia && token !== K.MultiLineCommentTrivia) { continue; }
    if (!commentAt.get(name).has(scanner.getTokenPos())) {
      throw Error(`Unassigned comment in ${name}: ${scanner.getTokenText()}`);
    }
  }
}

function variant(schema, type) {
  if (schema.type === type) { return schema; }
  for (const choice of schema.anyOf ?? []) {
    const result = variant(choice, type);
    if (result) { return result; }
  }
}

function tightenMetadata(schema) {
  // Metadata tests allow 16 conditions, or one per include/exclude side.
  const list = variant(schema, 'array');
  const comparison = variant(schema, 'object');
  list.maxItems = 16;
  comparison.minProperties = 1;
  for (const test of [list.items, comparison.properties.include.items, comparison.properties.exclude.items]) {
    test.properties.key.minLength = 1;
    Object.assign(test.properties.any_of, {minItems: 1, maxItems: 64});
  }
}

function groupMode(side) {
  const mode = side + '_mode';
  return {
    if: {properties: {[side]: {minItems: 2}}, required: [side]},
    then: {required: [mode]},
    else: {not: {required: [mode]}},
  };
}

function applyConstraints(contracts) {
  const props = name => contracts[name].input_schema.properties;
  for (const {input_schema} of Object.values(contracts)) {
    const connection = input_schema.properties.connection_id;
    if (connection) { Object.assign(connection, {pattern: '^[0-9a-f]{32}$', minLength: 32, maxLength: 32}); }
  }
  for (const name of ['connect_03-start_session', 'connect_05-close_session']) {
    Object.assign(props(name).request_id, {minLength: 1, maxLength: 128});
  }

  const inspect = props('inspect_02-get_objects');
  const filters = variant(inspect.filters, 'object').properties;
  for (const key of ['layer', 'block', 'material', 'name', 'object_type', 'group']) {
    const terms = filters[key];
    terms.minProperties = 1;
    for (const side of ['include', 'exclude']) {
      Object.assign(terms.properties[side], {minItems: 1, maxItems: 64});
      terms.properties[side].items.minLength = 1;
    }
  }
  filters.name_contains.maxLength = 256;
  filters.group.allOf = ['include', 'exclude'].map(groupMode);
  for (const filter of [filters.user_text, filters.user_dictionary, props('intersect_02-resolve').user_dictionary]) {
    tightenMetadata(filter);
  }

  // Handler-enforced ranges supplement bounds that TypeScript primitives cannot express.
  const bounds = {
    'context_04-get_project_info': {files_limit: [1, 500], files_offset: [0]},
    'script_01-run_project_python': {timeout_seconds: [1, 600]},
    'script_02-run_rhino': {timeout_seconds: [1, 600]},
    'script_03-get_execution': {limit: [1, 1000], offset: [0]},
    'inspect_02-get_objects': {limit: [1, 200], offset: [0, 100000], depth: [1, 8],
                              face_limit: [1, 128], face_offset: [0, 100000]},
    'model_02-edit_planar_face': {expected_geometry_crc: [0, 0xFFFFFFFF], face_index: [0, 0x7FFFFFFF]},
    'capture_02-inspection': {columns: [1, 16], width: [128, 2048], height: [128, 2048]},
    'capture_03-current_view': {depth: [1, 8], width: [128, 2048], height: [128, 2048], scale_percent: [1, 100]},
    'capture_04-defined_view': {depth: [1, 8], width: [128, 2048], height: [128, 2048], scale_percent: [1, 100]},
    'asset_07-prepare': {limit: [1, 200], offset: [0]},
  };
  for (const [name, fields] of Object.entries(bounds)) {
    for (const [key, [minimum, maximum]] of Object.entries(fields)) {
      Object.assign(props(name)[key], {minimum, ...(maximum !== undefined && {maximum})});
    }
  }
  const step = props('plan_08-list').request.anyOf.find(s => s.properties.target.const === 'step');
  Object.assign(step.properties.limit, {minimum: 1, maximum: 500});
  props('capture_05-manipulate_view').factor.exclusiveMinimum = 0;

  for (const [key, maxItems] of Object.entries({group_ids: 64, object_ids: 4096})) {
    Object.assign(variant(inspect[key], 'array'), {minItems: 1, maxItems, uniqueItems: true});
  }
  Object.assign(variant(inspect.fields, 'array'), {minItems: 1, uniqueItems: true});
  inspect.expected_snapshot.pattern = '^(?:[0-9a-f]{64})?$';
  const crcs = variant(inspect.expected_geometry_crcs, 'object');
  crcs.maxProperties = 4096;
  Object.assign(crcs.additionalProperties, {minimum: 0, maximum: 0xFFFFFFFF});
  const inspection = props('capture_02-inspection');
  Object.assign(inspection.views, {minItems: 1, maxItems: 16});
  const tile = inspection.views.items.properties;
  Object.assign(tile.object_ids, {maxItems: 512, uniqueItems: true});
  tile.display_mode.maxLength = 512;
  tile.label.maxLength = 120;
  Object.assign(inspection.object_ids, {minItems: 1, maxItems: 4096, uniqueItems: true});
  Object.assign(props('model_03-edit_planar_faces').edits, {minItems: 1, maxItems: 32});
  props('drawing_06-generate_plan_section').clipping_ids.minItems = 1;
}

function layout(value, depth = 0) {
  const prefix = '  '.repeat(depth);
  const indent = prefix + '  ';
  const kind = Array.isArray(value) ? 'array' : typeof value;
  if (value === null || !['object', 'array'].includes(kind)) { return JSON.stringify(value); }
  const pairs = kind === 'object' ? Object.entries(value) : value;
  const single = kind === 'object'
    ? '{' + pairs.map(([key, item]) => JSON.stringify(key) + ': ' + JSON.stringify(item)).join(', ') + '}'
    : '[' + pairs.map(item => JSON.stringify(item)).join(', ') + ']';
  if (!pairs.length || depth > 2 && prefix.length + single.length < 105) { return single; }
  const lines = kind === 'object'
    ? pairs.map(([key, item]) => indent + JSON.stringify(key) + ': ' + layout(item, depth + 1))
    : pairs.map(item => indent + layout(item, depth + 1));
  const [open, close] = kind === 'object' ? '{}' : '[]';
  return open + '\n' + lines.join(',\n') + '\n' + prefix + close;
}

function compile() {
  const markdown = fs.readFileSync(SOURCE, 'utf8').replace(/\r\n?/g, '\n');
  const sections = [...markdown.matchAll(/^### ([\w-]+)\n\n([\s\S]*?)\n\n```ts\n([\s\S]+?)\n```/gm)];
  const names = [...markdown.matchAll(/^### ([\w-]+)$/gm)].map(([, name]) => name);
  if (!names.length || new Set(names).size !== names.length ||
      !same(names, sections.map(([, name]) => name))) {
    throw Error('Every tool heading must have one unique name and one TypeScript declaration.');
  }
  const declarations = sections.map(readDeclaration);
  const contracts = Object.fromEntries(declarations.map(d => [
    d.name,
    {description: d.description, input_schema: root(convert(d.input, true), true),
     payload_schema: root(convert(d.output, false), false), wrapped: d.wrapped},
  ]));
  declarations.forEach(checkComments);
  applyConstraints(contracts);

  const source_sha256 = createHash('sha256').update(markdown, 'utf8').digest('hex');
  return layout({source_sha256, tools: contracts}) + '\n';
}

try {
  const result = compile();
  if (options.check) {
    if (!fs.existsSync(TARGET) || fs.readFileSync(TARGET, 'utf8').replace(/\r\n/g, '\n') !== result) {
      throw Error('public_contract_data.json is out of date. Run compile_tool_contracts.cjs without --check.');
    }
    console.log('Public tool declarations match the packaged schemas.');
  } else {
    fs.writeFileSync(TARGET, result);
  }
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
}
