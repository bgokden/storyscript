# -*- coding: utf-8 -*-

from storyscript.parser import Tree

from .ExpressionResolver import ExpressionResolver
from .PathResolver import PathResolver
from .ReturnVisitor import ReturnVisitor
from .SymbolResolver import SymbolResolver
from .symbols.Scope import Scope
from .symbols.SymbolTypes import AnyType, NoneType
from .symbols.Symbols import Symbol


class ScopeSelectiveVisitor:
    """
    A selective visitor which only visits defined nodes.
    visit_children must be called explicitly.
    """
    def visit(self, tree, scope=None):
        if hasattr(self, tree.data):
            return getattr(self, tree.data)(tree, scope)

    def visit_children(self, tree, scope):
        for c in tree.children:
            if isinstance(c, Tree):
                self.visit(c, scope)


class TypeResolver(ScopeSelectiveVisitor):
    """
    Tries to resolve the type of a variable or function call.
    """
    def __init__(self):
        self.symbol_resolver = SymbolResolver(scope=None)
        self.resolver = ExpressionResolver(
            symbol_resolver=self.symbol_resolver
        )
        self.path_symbol_resolver = SymbolResolver(
            scope=None, check_variable_existence=False)
        self.path_resolver = PathResolver(self.path_symbol_resolver)

    def assignment(self, tree, scope):
        self.symbol_resolver.update_scope(scope)
        self.path_symbol_resolver.update_scope(scope)

        target_symbol = self.path_resolver.path(tree.path)

        frag = tree.assignment_fragment
        expr_type = self.resolver.base_expression(frag.base_expression)

        if target_symbol.type() == NoneType.instance():
            sym = Symbol(target_symbol.name(), expr_type)
            scope.symbols().insert(sym.name(), sym)
        else:
            tree.expect(target_symbol.type().can_be_assigned(expr_type),
                        'type_assignment_different',
                        target=target_symbol._type,
                        source=expr_type)

        self.visit_children(tree, scope)

    def rules(self, tree, scope):
        self.visit_children(tree, scope)

    def block(self, tree, scope):
        self.visit_children(tree, scope)

    def nested_block(self, tree, scope):
        tree.scope = Scope(parent=scope)
        self.visit_children(tree, scope=tree.scope)

    def foreach_block(self, tree, scope):
        """
        Create a new scope and add output variables to it
        """
        tree.scope = Scope(parent=scope)
        for e in tree.foreach_statement.output.children:
            name = e.value
            sym = Symbol(name, AnyType.instance())
            tree.scope.insert(name, sym)
        for c in tree.nested_block.children:
            self.visit_children(tree.nested_block, scope=tree.scope)

    def while_block(self, tree, scope):
        self.visit_children(tree.nested_block, scope=scope)

    def when_block(self, tree, scope):
        self.visit_children(tree.nested_block, scope=scope)

    def if_block(self, tree, scope):
        self.if_statement(tree, scope)
        for c in tree.children[2:]:
            self.visit(c, scope)

    def if_statement(self, tree, scope):
        """
        If blocks don't create a new scope.
        """
        if_statement = tree.if_statement
        self.symbol_resolver.update_scope(scope)
        self.resolver.base_expression(if_statement.base_expression)
        self.visit_children(tree.nested_block, scope=scope)

    def elseif_block(self, tree, scope):
        """
        Else if blocks don't create a new scope.
        """
        if_statement = tree.elseif_statement
        self.symbol_resolver.update_scope(scope)
        self.resolver.base_expression(if_statement.base_expression)
        self.visit_children(tree.nested_block, scope=scope)

    def else_block(self, tree, scope):
        """
        Else blocks don't create a new scope.
        """
        self.symbol_resolver.update_scope(scope)
        self.visit_children(tree.nested_block, scope=scope)

    def try_block(self, tree, scope):
        self.visit_children(tree.nested_block, scope=scope)
        for c in tree.children[2:]:
            self.visit(c, scope)

    def catch_block(self, tree, scope):
        self.visit_children(tree, scope=scope)

    def finally_block(self, tree, scope):
        self.visit_children(tree, scope=scope)

    def function_block(self, tree, scope):
        scope, return_type = self.function_statement(tree.function_statement)
        self.visit_children(tree.nested_block, scope=scope)
        ReturnVisitor.check(tree, scope, return_type)

    def function_statement(self, tree):
        """
        Create a new scope _without_ a parent scope for this function.
        Prepopulate the scope with symbols from the function arguments.
        """
        scope = Scope.root()
        return_type = AnyType.instance()
        for c in tree.children:
            if isinstance(c, Tree) and c.data == 'typed_argument':
                name = c.child(0).value
                sym = Symbol(name, self.resolver.types(c.types))
                scope.insert(name, sym)
        if tree.function_output:
            return_type = self.resolver.types(tree.function_output.types)
        return scope, return_type

    def start(self, tree, scope=None):
        # create the root scope
        tree.scope = Scope.root()
        self.visit_children(tree, scope=tree.scope)
