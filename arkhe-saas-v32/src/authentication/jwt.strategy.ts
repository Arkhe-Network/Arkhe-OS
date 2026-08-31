// src/authentication/jwt.strategy.ts
import {inject} from '@loopback/core';
import {AuthenticationStrategy} from '@loopback/authentication';
import {TokenService} from '@loopback/authentication-jwt';
import {Request} from '@loopback/rest';
import {securityId, UserProfile} from '@loopback/security';
import {TokenServiceBindings} from '@loopback/authentication-jwt';

export class JWTStrategy implements AuthenticationStrategy {
  name = 'jwt';

  constructor(
    @inject(TokenServiceBindings.TOKEN_SERVICE)
    public tokenService: TokenService,
  ) {}

  async authenticate(request: Request): Promise<UserProfile | undefined> {
    const token = this.extractToken(request);
    if (!token) return undefined;

    const userProfile = await this.tokenService.verifyToken(token);
    return {
      [securityId]: userProfile.id,
      id: userProfile.id,
      name: userProfile.name,
      email: userProfile.email,
      roles: userProfile.roles,
    };
  }

  private extractToken(request: Request): string | undefined {
    const authHeader = request.headers.authorization;
    if (!authHeader) return undefined;
    const parts = authHeader.split(' ');
    if (parts.length !== 2 || parts[0] !== 'Bearer') return undefined;
    return parts[1];
  }
}