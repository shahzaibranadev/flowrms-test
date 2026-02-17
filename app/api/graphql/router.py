from strawberry.fastapi import GraphQLRouter
from app.api.graphql.schema import schema

graphql_router = GraphQLRouter(schema)
